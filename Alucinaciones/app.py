from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re  # <-- FIX: se usa en Tab 5

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.pdf_extract import extract_text_pages
from src.references import slice_references_section, extract_reference_lines
from src.doi_extract import extract_dois_from_text, assign_page
from src.doi_validate import validate_doi_http
from src.metadata import crossref_title_by_doi, crossref_search_by_bibliographic
from src.reporting import to_dataframe, make_txt_report


def unique_keep_order(items):
    """Elimina duplicados manteniendo el orden (evita error de PyArrow/Streamlit)."""
    return list(dict.fromkeys(items))


st.title("📄 Validador de DOIs en PDFs (ES/EN) — Modular")
st.markdown("Sube un PDF, extrae DOIs (priorizando *References/Referencias/Bibliografía*) y valida si resuelven.")

with st.sidebar:
    st.header("Parámetros")
    timeout = st.number_input("Timeout (s)", min_value=3, max_value=60, value=15, step=1)
    retries = st.number_input("Reintentos", min_value=1, max_value=6, value=3, step=1)
    workers = st.number_input("Hilos", min_value=1, max_value=20, value=8, step=1)

    st.divider()
    st.subheader("Títulos (API, no scraping)")
    fetch_titles = st.checkbox("Traer título por DOI (Crossref)", value=True)
    search_titles = st.checkbox("Buscar títulos en referencias sin DOI (Crossref search)", value=False)
    max_ref_lines = st.number_input("Máx. líneas a buscar", min_value=10, max_value=500, value=80, step=10)


uploaded_file = st.file_uploader("Selecciona un PDF", type=["pdf"])

if "doi_cache" not in st.session_state:
    st.session_state["doi_cache"] = {}
if "results_df" not in st.session_state:
    st.session_state["results_df"] = None


if uploaded_file is not None:
    pages_text, method = extract_text_pages(uploaded_file)
    st.success(f"Texto extraído usando: {method} | Páginas: {len(pages_text)}")

    full_text = "\n".join(pages_text)
    ref_text, s_line, e_line = slice_references_section(full_text)
    ref_detected = s_line is not None

    if ref_detected:
        st.info("Se detectó sección de referencias (ES/EN). Se prioriza esa zona.")
    else:
        st.warning("No se detectó encabezado claro de referencias. Se usa documento completo.")

    dois_info = extract_dois_from_text(ref_text if ref_detected else full_text)

    # fallback si detectó referencias pero encontró muy pocos
    if ref_detected and len(dois_info) < 3:
        more = extract_dois_from_text(full_text)
        seen = {d["doi"].lower() for d in dois_info}
        for d in more:
            if d["doi"].lower() not in seen:
                dois_info.append(d)
                seen.add(d["doi"].lower())

    assign_page(dois_info, pages_text)
    st.write(f"DOIs únicos encontrados: **{len(dois_info)}**")

    if len(dois_info) == 0:
        st.stop()

    if st.button("🚀 Validar DOIs", type="primary"):
        progress = st.progress(0)
        status = st.empty()

        cache = st.session_state["doi_cache"]
        rows = []

        with ThreadPoolExecutor(max_workers=int(workers)) as ex:
            futures = {
                ex.submit(validate_doi_http, d["doi"], float(timeout), int(retries), cache): d
                for d in dois_info
            }
            done = 0
            for fut in as_completed(futures):
                d = futures[fut]
                doi, ok, cat, code, msg, rt = fut.result()

                rows.append(
                    {
                        "DOI": doi,
                        "Categoría": cat,
                        "Estado": "✅ Válido" if cat == "valid" else ("❌ Inválido" if cat == "invalid" else "⚠️ No verificable"),
                        "Código HTTP": code if code else "N/A",
                        "Mensaje": msg,
                        "Tiempo (s)": round(rt, 3),
                        "URL": f"https://doi.org/{doi}",
                        "Página": d.get("page", "N/A"),
                        "Patrón": d.get("pattern", ""),
                        "Contexto": d.get("context", ""),
                    }
                )
                done += 1
                progress.progress(done / len(dois_info))
                status.text(f"Validando {done}/{len(dois_info)} ...")

        df = to_dataframe(rows)

        if fetch_titles and not df.empty and "DOI" in df.columns:
            status.text("Consultando títulos por DOI (Crossref)...")
            titles, sources = [], []
            for doi in df["DOI"].astype(str).tolist():
                title, source = crossref_title_by_doi(doi, timeout=float(timeout))
                titles.append(title or "")
                sources.append(source or "")
            df["Título (Crossref)"] = titles
            df["Fuente (revista/editorial)"] = sources

        st.session_state["doi_cache"] = cache
        st.session_state["results_df"] = df
        status.text("✅ Listo")


df = st.session_state.get("results_df")
if df is not None and len(df) > 0:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Dashboard", "📋 Tabla", "🔍 Detalles", "📥 Exportar", "🧾 Referencias sin DOI"]
    )

    with tab1:
        total = len(df)
        # robustez: por si faltan categorías
        valid_count = int((df.get("Categoría", pd.Series([], dtype=str)) == "valid").sum())
        invalid_count = int((df.get("Categoría", pd.Series([], dtype=str)) == "invalid").sum())
        unknown_count = int((df.get("Categoría", pd.Series([], dtype=str)) == "unknown").sum())
        success_rate = (valid_count / total * 100) if total else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total DOIs", total)
        c2.metric("Válidos", valid_count)
        c3.metric("Inválidos", invalid_count)
        c4.metric("No verificables", unknown_count)
        st.caption(f"Tasa de éxito: {success_rate:.1f}% (unknown ≠ inválido)")

        colL, colR = st.columns(2)
        with colL:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["Válidos", "Inválidos", "No verificables"],
                        values=[valid_count, invalid_count, unknown_count],
                        hole=0.4,
                    )
                ]
            )
            fig.update_layout(height=360, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

        with colR:
            if "Código HTTP" in df.columns:
                codes = df["Código HTTP"].astype(str).value_counts().reset_index()
                codes.columns = ["Código", "Cantidad"]
                fig2 = px.bar(codes, x="Código", y="Cantidad", text="Cantidad")
                fig2.update_traces(textposition="outside")
                fig2.update_layout(height=360, margin=dict(t=20, b=20, l=10, r=10))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No hay columna 'Código HTTP' para graficar.")

        if "Tiempo (s)" in df.columns and "Categoría" in df.columns:
            fig3 = px.histogram(df, x="Tiempo (s)", color="Categoría", nbins=30)
            fig3.update_layout(height=360, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No hay columnas suficientes para el histograma de tiempos.")

    with tab2:
        filt = st.multiselect(
            "Filtrar por categoría",
            options=["valid", "invalid", "unknown"],
            default=["valid", "invalid", "unknown"],
        )
        dff = df[df["Categoría"].isin(filt)].copy() if "Categoría" in df.columns else df.copy()

        cols = ["DOI", "Estado", "Categoría", "Código HTTP", "Mensaje", "Tiempo (s)", "Página", "Patrón", "URL"]

        # Si existe Crossref, agregamos columnas de título/fuente sin duplicar "DOI"
        if "Título (Crossref)" in dff.columns:
            cols = ["Título (Crossref)", "Fuente (revista/editorial)"] + cols

        # FIX CRÍTICO: evitar columnas duplicadas
        cols = unique_keep_order(cols)

        # solo columnas que realmente existen (evita KeyError)
        cols = [c for c in cols if c in dff.columns]

        st.dataframe(
            dff[cols],
            use_container_width=True,
            height=560,
            column_config={"URL": st.column_config.LinkColumn("Enlace", display_text="Abrir")}
            if "URL" in dff.columns
            else None,
        )

    with tab3:
        if "Categoría" not in df.columns:
            st.info("No hay columna 'Categoría' para segmentar resultados.")
        else:
            inv = df[df["Categoría"] == "invalid"]
            unk = df[df["Categoría"] == "unknown"]
            val = df[df["Categoría"] == "valid"]

            with st.expander(f"❌ Inválidos ({len(inv)})", expanded=True):
                for _, r in inv.iterrows():
                    st.error(f"{r.get('DOI', '')} | {r.get('Mensaje', '')} | pág: {r.get('Página', 'N/A')}")
                    st.caption(r.get("Contexto", ""))

            with st.expander(f"⚠️ No verificables ({len(unk)})", expanded=False):
                for _, r in unk.iterrows():
                    st.warning(f"{r.get('DOI', '')} | {r.get('Mensaje', '')} | código: {r.get('Código HTTP', 'N/A')}")

            with st.expander(f"✅ Válidos ({len(val)})", expanded=False):
                for _, r in val.iterrows():
                    doi = r.get("DOI", "")
                    url = r.get("URL", "")
                    code = r.get("Código HTTP", "")
                    if url:
                        st.success(f"{doi} | HTTP {code} | [Abrir]({url})")
                    else:
                        st.success(f"{doi} | HTTP {code}")

    with tab4:
        csv_data = df.to_csv(index=False, encoding="utf-8")
        st.download_button(
            "Descargar CSV",
            data=csv_data,
            file_name=f"doi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
        st.download_button(
            "Descargar TXT",
            data=make_txt_report(df),
            file_name=f"doi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
        )

    with tab5:
        st.markdown("Búsqueda por API (Crossref) usando líneas de referencia sin DOI (no scraping).")
        if search_titles:
            if uploaded_file is None:
                st.info("Sube un PDF para habilitar esta sección.")
            else:
                pages_text, _ = extract_text_pages(uploaded_file)
                full_text = "\n".join(pages_text)
                ref_text, _, _ = slice_references_section(full_text)
                ref_lines = extract_reference_lines(ref_text)

                doi_present = re.compile(r"\b10\.\d{4,9}/", re.IGNORECASE)
                candidates = [ln for ln in ref_lines if not doi_present.search(ln)]
                candidates = candidates[: int(max_ref_lines)]

                out_rows = []
                with st.spinner("Buscando coincidencias (Crossref)..."):
                    for ln in candidates:
                        title, doi, source = crossref_search_by_bibliographic(ln, timeout=float(timeout))
                        if title or doi:
                            out_rows.append(
                                {
                                    "Referencia (línea)": ln,
                                    "Título encontrado": title or "",
                                    "DOI encontrado": doi or "",
                                    "Fuente": source or "",
                                    "URL": f"https://doi.org/{doi}" if doi else "",
                                }
                            )

                df_ref = pd.DataFrame(out_rows)

                # FIX: si por alguna razón se duplican nombres (raro, pero blindamos)
                df_ref = df_ref.loc[:, ~df_ref.columns.duplicated()]

                st.dataframe(
                    df_ref,
                    use_container_width=True,
                    height=560,
                    column_config={"URL": st.column_config.LinkColumn("Enlace", display_text="Abrir")}
                    if "URL" in df_ref.columns
                    else None,
                )
        else:
            st.info('Activa en la sidebar: “Buscar títulos en referencias sin DOI (Crossref search)”.')

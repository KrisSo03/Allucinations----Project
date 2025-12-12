from datetime import datetime
from typing import List, Dict
import pandas as pd


def to_dataframe(rows: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values(by=["Categoría", "Código HTTP", "DOI"], inplace=True, ignore_index=True)
    return df


def make_txt_report(df: pd.DataFrame) -> str:
    total = len(df)
    valid_count = int((df["Categoría"] == "valid").sum()) if total else 0
    invalid_count = int((df["Categoría"] == "invalid").sum()) if total else 0
    unknown_count = int((df["Categoría"] == "unknown").sum()) if total else 0

    lines = [
        "REPORTE DE VALIDACIÓN DE DOIs",
        "=" * 72,
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Total: {total}",
        f"Válidos: {valid_count}",
        f"Inválidos: {invalid_count}",
        f"No verificables: {unknown_count}",
        "",
        "-" * 72,
    ]
    for _, r in df.iterrows():
        extra = ""
        if "Título (Crossref)" in df.columns and str(r.get("Título (Crossref)", "")).strip():
            extra = f" | Título: {r.get('Título (Crossref)')}"
        lines.append(f"{r['Estado']} | {r['DOI']} | HTTP={r['Código HTTP']} | {r['Mensaje']}{extra}")
    return "\n".join(lines)

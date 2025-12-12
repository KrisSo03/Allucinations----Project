import re
from typing import Dict, List
from .pdf_extract import normalize_text

DOI_PATTERNS = [
    r"doi:\s*(10\.\d{4,9}(?:\.\d+)*\/(?:(?![\"&\'<>])\S)+)",
    r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}(?:\.\d+)*\/(?:(?![\"&\'<>])\S)+)",
    r"(?:^|[\s\(\[{,;:])(10\.\d{4,9}(?:\.\d+)*\/(?:(?![\"&\'<>])\S)+)",
    r"[\[\(\{](10\.\d{4,9}(?:\.\d+)*\/(?:(?![\"&\'<>])\S)+)[\]\)\}]",
    r"(?:DOI|doi|Doi)[\s:]+(10\.\d{4,9}(?:\.\d+)*\/(?:(?![\"&\'<>])\S)+)",
]


def clean_doi(doi: str) -> str:
    doi = normalize_text(doi)
    doi = re.sub(r"\s+", "", doi)
    doi = (
        doi.replace("&quot;", "")
        .replace("&#34;", "")
        .replace("&nbsp;", "")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    doi = re.sub(r"[.,;:)\]}\'\"]+$", "", doi)
    doi = re.sub(r"\.{2,}$", "", doi)
    return doi.strip()


def is_valid_doi_format(doi: str) -> bool:
    if not re.match(r"^10\.\d{4,9}(?:\.\d+)*\/.+$", doi):
        return False
    parts = doi.split("/", 1)
    if len(parts) < 2:
        return False
    suffix = parts[1].strip()
    if len(suffix) < 2:
        return False
    invalid_chars = ['<', '>', '"', "{", "}", "|", "\\", "^", "`", " "]
    if any(ch in doi for ch in invalid_chars):
        return False
    if suffix.strip(".,;:!?-_") == "":
        return False
    return True


def extract_dois_from_text(text: str) -> List[Dict]:
    out: List[Dict] = []
    seen = set()
    text_norm = re.sub(r"\s+", " ", normalize_text(text))

    for idx, pat in enumerate(DOI_PATTERNS, 1):
        for m in re.finditer(pat, text_norm, flags=re.IGNORECASE | re.MULTILINE):
            raw = m.group(1) if m.lastindex else m.group(0)
            doi = clean_doi(raw)
            if not is_valid_doi_format(doi):
                continue
            key = doi.lower()
            if key in seen:
                continue
            seen.add(key)

            start = max(m.start() - 80, 0)
            end = min(m.end() + 80, len(text_norm))
            context = " ".join(text_norm[start:end].split())

            out.append(
                {"doi": doi, "raw": raw, "pattern": f"Patrón {idx}", "position": m.start(), "context": context}
            )

    out.sort(key=lambda x: x["position"])
    return out


def assign_page(dois_info: List[Dict], pages_text: List[str]) -> None:
    for d in dois_info:
        d["page"] = "N/A"
        target = d["doi"].lower()
        for pi, ptxt in enumerate(pages_text, 1):
            if target in (ptxt or "").lower():
                d["page"] = pi
                break

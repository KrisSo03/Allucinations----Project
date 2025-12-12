from typing import Optional, Tuple
import requests


def crossref_title_by_doi(doi: str, timeout: float = 15.0) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns: (title, container_or_publisher)
    """
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "doi-validator/1.0 (mailto:example@example.com)"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None, None
        data = r.json().get("message", {}) or {}
        title_list = data.get("title") or []
        title = title_list[0].strip() if title_list else None
        container = (data.get("container-title") or [None])[0]
        publisher = data.get("publisher")
        return title, (container or publisher)
    except Exception:
        return None, None


def crossref_search_by_bibliographic(ref_line: str, timeout: float = 15.0) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Returns: (matched_title, matched_doi, matched_container_or_publisher)
    """
    q = (ref_line or "").strip()
    if len(q) < 20:
        return None, None, None

    url = "https://api.crossref.org/works"
    params = {"query.bibliographic": q, "rows": 1}
    headers = {"User-Agent": "doi-validator/1.0 (mailto:example@example.com)"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None, None, None
        items = (r.json().get("message", {}) or {}).get("items", []) or []
        if not items:
            return None, None, None
        item = items[0]
        title_list = item.get("title") or []
        title = title_list[0].strip() if title_list else None
        doi = item.get("DOI")
        container = (item.get("container-title") or [None])[0]
        publisher = item.get("publisher")
        return title, doi, (container or publisher)
    except Exception:
        return None, None, None

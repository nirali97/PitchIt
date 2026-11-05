"""Dependency-free evidence extraction. Quotes are always verbatim spans of the
candidate's text (never fabricated); `is_verbatim` lets callers re-validate."""
import re

_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text) if s.strip()]


def is_verbatim(quote: str, source: str) -> bool:
    return bool(quote) and quote in source


def find_evidence(text: str, keywords: list[str], max_items: int = 2, max_len: int = 240) -> list[dict]:
    """Return up to max_items sentences from `text` containing any keyword (case-insensitive)."""
    kws = [k.lower() for k in keywords]
    out: list[dict] = []
    for s in sentences(text):
        low = s.lower()
        hit = next((k for k in kws if k in low), None)
        if hit:
            q = s if len(s) <= max_len else s[:max_len]
            out.append({"quote": q, "matched": hit})
            if len(out) == max_items:
                break
    return out

"""Helpers that control which messages and citations the coach may use."""
import re


def model_history(messages, active_hash):
    """Exclude conversation turns that were grounded in a different/removed PDF."""
    return [
        message for message in messages
        if not message.get("doc_hash") or message.get("doc_hash") == active_hash
    ]


_CITATION_PATTERN = re.compile(
    r"\[source:\s*([^,\]\n]+),\s*p\.\s*(\d+)\]",
    flags=re.IGNORECASE,
)


def validate_coach_citations(answer, retrieved_hits, active_pdf_hash):
    """Keep only filename/page citations that exist in the current retrieved passages."""
    if not active_pdf_hash or not retrieved_hits:
        return _CITATION_PATTERN.sub("", answer).strip()

    valid_references = {
        (str(hit.get("source", "")).strip(), int(hit.get("page", 0)))
        for hit in retrieved_hits
        if hit.get("source") and hit.get("page") is not None
    }

    def replace_unverified(match):
        filename = match.group(1).strip()
        try:
            page = int(match.group(2))
        except ValueError:
            return "[unverified reference removed]"
        if (filename, page) not in valid_references:
            return "[unverified reference removed]"
        return match.group(0)

    return _CITATION_PATTERN.sub(replace_unverified, answer).strip()
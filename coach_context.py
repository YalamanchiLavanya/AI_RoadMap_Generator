"""Helpers that control which messages and citations the coach may use."""
import re


def model_history(messages, active_hash):
    """Exclude conversation turns that were grounded in a different/removed PDF."""
    return [
        message for message in messages
        if not message.get("doc_hash") or message.get("doc_hash") == active_hash
    ]


# Canonical format (required by COACH_SYSTEM_PROMPT):  (filename.pdf, p. 3)
# Old bracket format still accepted so earlier saved answers keep working.
_PAREN = re.compile(r"\(\s*([^(),\n]+?\.pdf)\s*,\s*pp?\.\s*(\d+)\s*\)", re.IGNORECASE)
_BRACKET = re.compile(
    r"\[\s*source:\s*([^,\]\n]+?)\s*,\s*pp?\.\s*(\d+)\s*\]", re.IGNORECASE
)
REMOVED_MARKER = "[unverified reference removed]"


def validate_coach_citations(answer, retrieved_hits, active_pdf_hash):
    """Keep only filename/page citations that exist in the current retrieved passages."""
    if not active_pdf_hash or not retrieved_hits:
        answer = _PAREN.sub("", answer)
        answer = _BRACKET.sub("", answer)
        return re.sub(r"[ \t]{2,}", " ", answer).strip()

    valid = set()
    for hit in retrieved_hits:
        source, page = hit.get("source"), hit.get("page")
        if source and page is not None:
            valid.add((str(source).strip().lower(), int(page)))

    def check(match):
        key = (match.group(1).strip().lower(), int(match.group(2)))
        return match.group(0) if key in valid else REMOVED_MARKER

    answer = _PAREN.sub(check, answer)
    answer = _BRACKET.sub(check, answer)
    return answer.strip()
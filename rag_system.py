"""PDF extraction, indexing, and retrieval - with page references.

Rules this module enforces
--------------------------
* Every chunk remembers the page it came from, so answers can cite pages.
* The app holds at most ONE index, and it always belongs to the file currently
  selected in the uploader. Removing or replacing the file clears the old index
  (``sync_pdf_state``), so old content can never be answered as if it were new.
* FAISS is used when installed; otherwise search falls back to plain NumPy with
  the same results, so the app still works (and tests run) without it.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import Any, Callable, MutableMapping

import numpy as np

from config import (
    EMBEDDING_MODEL_NAME,
    MAX_PDF_MB,
    PDF_CHUNK_OVERLAP,
    PDF_CHUNK_SIZE,
    RETRIEVAL_MIN_SCORE,
    RETRIEVAL_TOP_K,
)

PDF_STATE_KEY = "pdf_index"

Embedder = Callable[[list[str]], Any]


class PdfError(ValueError):
    """A PDF problem that can be explained to the learner."""


@dataclass
class PageText:
    number: int  # 1-based, as printed in a PDF viewer
    text: str


@dataclass
class ExtractedPdf:
    pages: list[PageText]
    page_count: int


def file_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Extraction and chunking
# --------------------------------------------------------------------------
def extract_pages(pdf_bytes: bytes) -> ExtractedPdf:
    from pypdf import PdfReader

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:  # noqa: BLE001
        raise PdfError(f"The file could not be read as a PDF ({type(exc).__name__}).") from exc

    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception:  # noqa: BLE001
            unlocked = 0
        if not unlocked:
            raise PdfError("This PDF is password-protected. Remove the password and upload it again.")

    pages: list[PageText] = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - one bad page should not lose the document
            text = ""
        text = " ".join(text.split())
        if text:
            pages.append(PageText(number, text))
    if not pages:
        raise PdfError(
            "No extractable text was found. Try a text-based PDF instead of a scanned document."
        )
    return ExtractedPdf(pages=pages, page_count=len(reader.pages))


def chunk_pages(
    pages: list[PageText], size: int = PDF_CHUNK_SIZE, overlap: int = PDF_CHUNK_OVERLAP
) -> list[dict]:
    """Split each page into overlapping chunks. A chunk never crosses a page."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and larger than the overlap")
    chunks: list[dict] = []
    for page in pages:
        text, start = page.text, 0
        while start < len(text):
            piece = text[start : start + size].strip()
            if piece:
                chunks.append({"id": len(chunks), "page": page.number, "text": piece})
            if start + size >= len(text):
                break
            start += size - overlap
    if not chunks:
        raise PdfError("No usable text chunks were created from this PDF.")
    return chunks


# --------------------------------------------------------------------------
# Embeddings and the index
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_sentence_transformer():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def default_embedder(texts: list[str]) -> np.ndarray:
    model = _load_sentence_transformer()
    return np.asarray(model.encode(texts, normalize_embeddings=True, convert_to_numpy=True), dtype="float32")


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.ascontiguousarray(matrix, dtype="float32")
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _build_faiss(matrix: np.ndarray):
    try:
        import faiss
    except ImportError:
        return None
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    return index


@dataclass
class PdfIndex:
    filename: str
    file_hash: str
    page_count: int
    chunks: list[dict]
    embed_fn: Embedder
    matrix: np.ndarray
    faiss_index: Any = None

    @property
    def backend(self) -> str:
        return "faiss" if self.faiss_index is not None else "numpy"

    @property
    def indexed_pages(self) -> list[int]:
        return sorted({chunk["page"] for chunk in self.chunks})

    def search(
        self, query: str, top_k: int = RETRIEVAL_TOP_K, min_score: float = RETRIEVAL_MIN_SCORE
    ) -> list[dict]:
        if not query.strip() or not self.chunks:
            return []
        vector = _l2_normalize(np.asarray(self.embed_fn([query]), dtype="float32"))
        k = min(top_k, len(self.chunks))
        if self.faiss_index is not None:
            scores, ids = self.faiss_index.search(vector, k)
            pairs = list(zip(scores[0], ids[0]))
        else:
            similarities = self.matrix @ vector[0]
            order = np.argsort(-similarities)[:k]
            pairs = [(similarities[i], i) for i in order]
        return [
            {
                "source": self.filename,
                "page": self.chunks[int(i)]["page"],
                "text": self.chunks[int(i)]["text"],
                "score": round(float(score), 3),
            }
            for score, i in pairs
            if int(i) >= 0 and float(score) >= min_score
        ]


def build_pdf_index(
    pdf_bytes: bytes, filename: str, embed_fn: Embedder | None = None
) -> PdfIndex:
    if len(pdf_bytes) > MAX_PDF_MB * 1024 * 1024:
        raise PdfError(f"The PDF is larger than {MAX_PDF_MB} MB.")
    extracted = extract_pages(pdf_bytes)
    chunks = chunk_pages(extracted.pages)
    embed = embed_fn or default_embedder
    try:
        matrix = _l2_normalize(np.asarray(embed([c["text"] for c in chunks]), dtype="float32"))
    except Exception as exc:  # noqa: BLE001
        raise PdfError(f"The document could not be embedded: {exc}") from exc
    return PdfIndex(
        filename=filename,
        file_hash=file_digest(pdf_bytes),
        page_count=extracted.page_count,
        chunks=chunks,
        embed_fn=embed,
        matrix=matrix,
        faiss_index=_build_faiss(matrix),
    )


# --------------------------------------------------------------------------
# Session-state rules (work on any mapping, including st.session_state)
# --------------------------------------------------------------------------
def get_pdf_index(state: MutableMapping) -> PdfIndex | None:
    return state.get(PDF_STATE_KEY)


def set_pdf_index(state: MutableMapping, index: PdfIndex) -> str | None:
    """Store an index, replacing any old one. Returns the replaced filename."""
    previous = get_pdf_index(state)
    state[PDF_STATE_KEY] = index
    return previous.filename if previous else None


def clear_pdf_index(state: MutableMapping) -> str | None:
    """Remove the index. Returns the removed filename (None if there was none)."""
    previous = get_pdf_index(state)
    state[PDF_STATE_KEY] = None
    return previous.filename if previous else None


def sync_pdf_state(state: MutableMapping, uploaded_hash: str | None) -> str:
    """Keep the index in step with the file selected in the uploader.

    Returns "none" (nothing indexed), "current" (index matches the file),
    "removed" (file removed, index cleared) or "replaced" (a different file was
    selected, old index cleared - the new file needs indexing).
    """
    index = get_pdf_index(state)
    if index is None:
        return "none"
    if uploaded_hash is None:
        clear_pdf_index(state)
        return "removed"
    if uploaded_hash != index.file_hash:
        clear_pdf_index(state)
        return "replaced"
    return "current"


# --------------------------------------------------------------------------
# Retrieval helpers
# --------------------------------------------------------------------------
def retrieve(state: MutableMapping, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
    index = get_pdf_index(state)
    return index.search(query, top_k=top_k) if index else []


def generation_query(profile) -> str:
    return (
        f"{profile.goal}. Skills: {profile.current_skills}. "
        "syllabus topics modules prerequisites learning outcomes"
    )


def retrieve_for_generation(state: MutableMapping, profile, top_k: int = 6) -> list[dict]:
    """Excerpts used when generating the first roadmap, ordered by page."""
    hits = retrieve(state, generation_query(profile), top_k=top_k)
    return sorted(hits, key=lambda hit: hit["page"])


def summarize_sources(hits: list[dict]) -> str:
    """'syllabus.pdf p. 2, 5' - for captions under answers."""
    if not hits:
        return ""
    by_file: dict[str, set[int]] = {}
    for hit in hits:
        by_file.setdefault(hit["source"], set()).add(int(hit["page"]))
    return "; ".join(
        f"{name} p. {', '.join(str(p) for p in sorted(pages))}" for name, pages in by_file.items()
    )

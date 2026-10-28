
# rag_system.py

import re
import numpy as np
import faiss

from pypdf import PdfReader


# Store the PDF search index and its metadata
class PDFKnowledgeBase:
    def __init__(self):
        # FAISS index
        self.index = None

        # Text chunks and their page information
        self.chunks = []

        # Embedding model
        self.embedding_model = None

        # Uploaded PDF name
        self.filename = None

    # Load the embedding model only when needed
    def _load_embedding_model(self):
        if self.embedding_model is None:
            # Load PyTorch only when PDF embeddings are actually needed
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer(
                "all-MiniLM-L6-v2"
            )

        return self.embedding_model
    # Split a page into smaller text chunks
    def _split_text(self, text, chunk_size=1000, overlap=150):
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(chunk_text)

            if end == len(text):
                break

            start = end - overlap

        return chunks

    # Read the uploaded PDF and build the search index
    def build_index(self, uploaded_file):
        if uploaded_file is None:
            raise ValueError("Please upload a PDF file.")

        filename = getattr(uploaded_file, "name", "uploaded.pdf")

        # Clear the previous PDF index before processing a replacement
        self.clear()

        try:
            reader = PdfReader(uploaded_file)

            new_chunks = []

            # Keep the original PDF page number with every chunk
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""

                for chunk_text in self._split_text(page_text):
                    new_chunks.append(
                        {
                            "text": chunk_text,
                            "page": page_number,
                            "filename": filename,
                        }
                    )

            if not new_chunks:
                raise ValueError(
                    "No readable text was found in this PDF. "
                    "It may contain scanned images and require OCR."
                )

            # Create embeddings for all extracted chunks
            model = self._load_embedding_model()

            texts = [chunk["text"] for chunk in new_chunks]

            embeddings = model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            embeddings = np.asarray(
                embeddings,
                dtype=np.float32,
            )

            # Build a cosine-similarity index
            new_index = faiss.IndexFlatIP(
                embeddings.shape[1]
            )

            new_index.add(embeddings)

            # Save the new index only after successful processing
            self.index = new_index
            self.chunks = new_chunks
            self.filename = filename

            return {
                "filename": filename,
                "pages": len(reader.pages),
                "chunks": len(new_chunks),
                "message": "PDF indexed successfully.",
            }

        except Exception:
            # Do not leave a partial or stale index after failure
            self.clear()
            raise

    # Search the PDF for information related to a question
    def search(self, query, top_k=4):
        if not query or not query.strip():
            return ""

        if self.index is None or not self.chunks:
            return ""

        if top_k < 1:
            return ""

        model = self._load_embedding_model()

        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        # Retrieve the most relevant chunks
        result_count = min(top_k, len(self.chunks))

        scores, indices = self.index.search(
            query_embedding,
            result_count,
        )

        retrieved_parts = []

        for score, chunk_index in zip(
            scores[0],
            indices[0],
        ):
            if chunk_index < 0:
                continue

            chunk = self.chunks[chunk_index]

            retrieved_parts.append(
                f"[Source: {chunk['filename']}, "
                f"Page {chunk['page']}, "
                f"Similarity: {float(score):.3f}]\n"
                f"{chunk['text']}"
            )

        return "\n\n".join(retrieved_parts)

    # Remove the active PDF and its search index
    def clear(self):
        self.index = None
        self.chunks = []
        self.filename = None

    # Check whether a PDF is currently indexed
    def is_ready(self):
        return self.index is not None and bool(self.chunks)


# Create a reusable knowledge base for the Streamlit session
def create_knowledge_base():
    return PDFKnowledgeBase()

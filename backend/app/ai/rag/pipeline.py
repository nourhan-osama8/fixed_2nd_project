"""
RAG pipeline — FAISS + sentence-transformers.

Responsibilities:
  - Load TXT, PDF, and DOCX files from the RAG documents folder.
  - Chunk text with overlap.
  - Embed chunks using a local sentence-transformers model.
  - Store vectors in a FAISS IndexFlatIP (inner-product / cosine similarity).
  - Expose search(question, k) for retrieval.
  - Expose a module-level singleton `rag` that is built lazily on first use
    and can be rebuilt after new documents are uploaded.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

from app.core.config import settings
from app.ai.rag.config import CHUNK_SIZE, CHUNK_OVERLAP, TOP_K

logger = logging.getLogger("nileconnect")

# ── Document loading ──────────────────────────────────────────────────────────

def _load_docx(file_path: Path) -> str:
    """Extract all paragraph text from a DOCX file."""
    try:
        import docx  # python-docx
        doc = docx.Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        logger.warning("python-docx is not installed — cannot parse DOCX files. Run: pip install python-docx")
        return ""
    except Exception as exc:
        logger.warning("Could not parse DOCX %s: %s", file_path, exc)
        return ""


def load_documents(folder: str) -> List[Dict[str, str]]:
    """Load all .txt, .pdf, and .docx files from *folder* recursively."""
    folder_path = Path(folder)
    documents: List[Dict[str, str]] = []

    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        return documents

    for file_path in folder_path.rglob("*"):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".txt":
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                if text.strip():
                    documents.append({"source": str(file_path), "text": text})

            elif suffix == ".pdf":
                reader = PdfReader(str(file_path))
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        documents.append({
                            "source": f"{file_path}#page={page_num + 1}",
                            "text": text,
                        })

            elif suffix == ".docx":
                text = _load_docx(file_path)
                if text.strip():
                    documents.append({"source": str(file_path), "text": text})

        except Exception as exc:
            logger.warning("Could not load %s: %s", file_path, exc)

    logger.info("RAG: found %d document sections across %d file types in %s",
                len(documents), len({Path(d["source"].split("#")[0]).suffix for d in documents}), folder)
    return documents



# ── Text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split *text* into overlapping chunks."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap

    return chunks


# ── SimpleRAG ─────────────────────────────────────────────────────────────────

class SimpleRAG:
    """
    In-memory FAISS RAG backed by sentence-transformers embeddings.

    Thread-safe: rebuilds are serialised with a lock.
    """

    def __init__(self, model_name: str | None = None):
        model_name = model_name or settings.EMBEDDING_MODEL
        logger.info("Loading embedding model: %s", model_name)
        self.embedder = SentenceTransformer(model_name)
        self.index: faiss.IndexFlatIP | None = None
        self.chunks: List[Dict[str, str]] = []
        self._lock = threading.Lock()
        self._built = False

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self, folder: str | None = None) -> None:
        """(Re)build the FAISS index from documents in *folder*."""
        folder = folder or settings.rag_docs_dir_abs

        with self._lock:
            documents = load_documents(folder)
            logger.info("RAG: loaded %d document pages from %s", len(documents), folder)

            self.chunks = []
            for doc in documents:
                for piece in chunk_text(doc["text"]):
                    self.chunks.append({"text": piece, "source": doc["source"]})

            logger.info("RAG: created %d chunks", len(self.chunks))

            if not self.chunks:
                logger.warning("RAG: no documents found — index is empty.")
                self.index = None
                self._built = True
                return

            texts = [c["text"] for c in self.chunks]
            embeddings = self.embedder.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=64,
            )
            embeddings = np.asarray(embeddings, dtype="float32")

            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(embeddings)

            logger.info("RAG: FAISS index built with %d vectors (dim=%d)", self.index.ntotal, dimension)
            self._built = True

    def ensure_built(self) -> None:
        """Build on first call only (lazy init)."""
        if not self._built:
            self.build()

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, question: str, k: int = TOP_K) -> List[Dict[str, Any]]:
        """Return the top-k most relevant chunks for *question*."""
        self.ensure_built()

        if self.index is None or self.index.ntotal == 0:
            return []

        query_emb = self.embedder.encode([question], normalize_embeddings=True)
        query_emb = np.asarray(query_emb, dtype="float32")

        scores, indices = self.index.search(query_emb, min(k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = self.chunks[idx]
            results.append({
                "score": float(score),
                "source": item["source"],
                "text": item["text"],
            })

        return results

    # ── Info ──────────────────────────────────────────────────────────────────

    @property
    def document_count(self) -> int:
        return len(self.chunks)

    @property
    def is_ready(self) -> bool:
        return self._built and self.index is not None and self.index.ntotal > 0


# ── Module-level singleton ────────────────────────────────────────────────────

rag: SimpleRAG = SimpleRAG()

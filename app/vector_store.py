"""
PDF Ingestion & Vector Store — parses the NG12 PDF, creates embeddings,
and stores them in ChromaDB for RAG retrieval.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from pypdf import PdfReader

from app.config import (
    GOOGLE_API_KEY,
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    PDF_DIR,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton for the vector store
# ---------------------------------------------------------------------------
_vector_store: Optional[Chroma] = None


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create the Google Generative AI embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )


def parse_pdf(pdf_path: str | Path) -> list[dict]:
    """
    Parse a PDF and return a list of dicts with keys:
      - text: the page text
      - page: 1-based page number
      - source: filename
    """
    pdf_path = Path(pdf_path)
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({
                "text": text.strip(),
                "page": i + 1,
                "source": pdf_path.name,
            })
    logger.info(f"Parsed {len(pages)} pages from {pdf_path.name}")
    return pages


def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Split page texts into smaller overlapping chunks.
    Each chunk retains its source page number and a unique chunk_id.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    chunk_counter = 0
    for page_data in pages:
        splits = splitter.split_text(page_data["text"])
        for split_text in splits:
            chunk_id = f"ng12_{page_data['page']:04d}_{chunk_counter:04d}"
            chunks.append({
                "text": split_text,
                "metadata": {
                    "source": page_data["source"],
                    "page": page_data["page"],
                    "chunk_id": chunk_id,
                },
            })
            chunk_counter += 1
    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks


def build_vector_store(pdf_path: Optional[str | Path] = None, force: bool = False) -> Chroma:
    """
    Build (or load) the ChromaDB vector store from the NG12 PDF.
    If the store already exists on disk and force=False, just load it.
    """
    global _vector_store

    persist_dir = CHROMA_PERSIST_DIR
    embeddings = _get_embeddings()

    # Check if store already exists
    if not force and os.path.exists(persist_dir) and os.listdir(persist_dir):
        logger.info(f"Loading existing vector store from {persist_dir}")
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=persist_dir,
            embedding_function=embeddings,
        )
        # Verify it has documents
        count = _vector_store._collection.count()
        if count > 0:
            logger.info(f"Vector store loaded with {count} documents")
            return _vector_store
        logger.warning("Vector store was empty, rebuilding...")

    # Find the PDF
    if pdf_path is None:
        pdf_candidates = list(PDF_DIR.glob("*.pdf"))
        if not pdf_candidates:
            raise FileNotFoundError(
                f"No PDF found in {PDF_DIR}. Please place the NG12 PDF there."
            )
        pdf_path = pdf_candidates[0]

    logger.info(f"Building vector store from {pdf_path}...")

    # Parse → Chunk → Embed → Store (in batches to respect rate limits)
    pages = parse_pdf(pdf_path)
    chunks = chunk_pages(pages)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Create empty vector store first
    _vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )

    # Add in small batches with delays to avoid rate limiting
    import time
    BATCH_SIZE = 20  # Small batches to stay under 100 requests/min
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_meta = metadatas[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info(f"Embedding batch {batch_num}/{total_batches} ({len(batch_texts)} chunks)...")
        _vector_store.add_texts(texts=batch_texts, metadatas=batch_meta)
        if i + BATCH_SIZE < len(texts):
            logger.info("Waiting 30s for rate limit...")
            time.sleep(30)

    count = _vector_store._collection.count()
    logger.info(f"Vector store built and persisted with {count} documents")
    return _vector_store


def get_vector_store() -> Chroma:
    """Get the singleton vector store instance (loads/builds if needed)."""
    global _vector_store
    if _vector_store is None:
        _vector_store = build_vector_store()
    return _vector_store


def search_guidelines(query: str, top_k: int = 5) -> list[dict]:
    """
    Search the NG12 vector store for chunks relevant to the query.
    Returns a list of dicts with keys: text, source, page, chunk_id, score.
    """
    store = get_vector_store()
    results = store.similarity_search_with_relevance_scores(query, k=top_k)

    retrieved = []
    for doc, score in results:
        retrieved.append({
            "text": doc.page_content,
            "source": doc.metadata.get("source", "NG12 PDF"),
            "page": doc.metadata.get("page", 0),
            "chunk_id": doc.metadata.get("chunk_id", "unknown"),
            "score": round(float(score), 4),
        })
    return retrieved
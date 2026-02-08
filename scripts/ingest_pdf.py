"""
PDF Ingestion Script — standalone script to parse the NG12 PDF
and build the ChromaDB vector index.

Usage:
    python -m scripts.ingest_pdf [--pdf-path /path/to/ng12.pdf] [--force]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.vector_store import build_vector_store, parse_pdf, chunk_pages
from app.config import PDF_DIR, CHROMA_PERSIST_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest NG12 PDF into vector store")
    parser.add_argument(
        "--pdf-path",
        type=str,
        default=None,
        help="Path to the NG12 PDF file. If not provided, searches data/ directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if vector store already exists.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics about the parsed PDF and chunks.",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path
    if pdf_path:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF not found at {pdf_path}")
            sys.exit(1)

    logger.info("=" * 60)
    logger.info("NG12 PDF Ingestion Pipeline")
    logger.info("=" * 60)

    if args.stats and pdf_path:
        logger.info("\n--- PDF Statistics ---")
        pages = parse_pdf(pdf_path)
        chunks = chunk_pages(pages)
        logger.info(f"Total pages parsed: {len(pages)}")
        logger.info(f"Total chunks created: {len(chunks)}")
        avg_len = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
        logger.info(f"Average chunk length: {avg_len:.0f} characters")
        logger.info(f"Min chunk length: {min(len(c['text']) for c in chunks)}")
        logger.info(f"Max chunk length: {max(len(c['text']) for c in chunks)}")

    logger.info(f"Persist directory: {CHROMA_PERSIST_DIR}")
    logger.info(f"Force rebuild: {args.force}")

    store = build_vector_store(pdf_path=pdf_path, force=args.force)
    count = store._collection.count()

    logger.info("=" * 60)
    logger.info(f"SUCCESS: Vector store ready with {count} document chunks.")
    logger.info(f"Stored at: {CHROMA_PERSIST_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
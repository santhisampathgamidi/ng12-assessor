"""Project settings pulled from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# File locations
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PATIENTS_FILE = DATA_DIR / "patients.json"
PDF_DIR = DATA_DIR  # Drop the NG12 PDF in this folder.

# Gemini + embeddings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

# Vector store
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ng12_guidelines")

# Retrieval settings
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "5"))

# API server
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

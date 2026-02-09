"""FastAPI entrypoint for the NG12 assessor service."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.models import (
    AssessmentRequest,
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
)
from app.patient_service import load_patients, list_patients_summary
from app.agent import assess_patient, chat, get_chat_history, clear_chat_history
from app.vector_store import get_vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Startup / shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up local data and vector store on startup."""
    logger.info("Starting NG12 Cancer Risk Assessor...")

    # Load patient records first so endpoints are ready immediately.
    load_patients()
    logger.info("Patient data loaded.")

    # Open vector store, or build it if it is missing.
    try:
        store = get_vector_store()
        count = store._collection.count()
        logger.info(f"Vector store ready with {count} documents.")
    except FileNotFoundError as e:
        logger.warning(f"Vector store not initialized: {e}")
        logger.warning("Run 'python -m scripts.ingest_pdf' to build the vector store.")
    except Exception as e:
        logger.warning(f"Vector store initialization issue: {e}")

    yield  # Application is now serving requests.

    logger.info("Shutting down NG12 Cancer Risk Assessor.")


# App setup
app = FastAPI(
    title="NG12 Cancer Risk Assessor",
    description=(
        "Clinical Decision Support Agent using NICE NG12 guidelines. "
        "Part 1: Patient risk assessment. Part 2: Conversational Q&A."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Serve static assets if the frontend build exists.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# Root / frontend
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Return the frontend entry page when available."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "NG12 Cancer Risk Assessor API. Visit /docs for API documentation."}


# Health check
@app.get("/health")
async def health_check():
    """Simple liveness endpoint."""
    return {"status": "healthy", "service": "ng12-cancer-risk-assessor"}


# Risk assessment endpoints
@app.get("/patients")
async def list_patients():
    """List patients for the UI dropdown."""
    return list_patients_summary()


@app.post("/assess")
async def assess(request: AssessmentRequest):
    """Run NG12 assessment for a patient id."""
    try:
        result = assess_patient(request.patient_id)
    except Exception as e:
        logger.exception(f"Assessment failed for {request.patient_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in result and result.get("risk_level") is None:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# Chat endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Answer NG12 questions with session-aware chat."""
    try:
        result = chat(
            session_id=request.session_id,
            message=request.message,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.exception(f"Chat failed for session {request.session_id}")
        raise HTTPException(status_code=500, detail=str(e))

    return result


@app.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def chat_history(session_id: str):
    """Get stored conversation history for one session."""
    history = get_chat_history(session_id)
    return ChatHistoryResponse(session_id=session_id, messages=history)


@app.delete("/chat/{session_id}")
async def delete_chat(session_id: str):
    """Delete stored conversation history for one session."""
    deleted = clear_chat_history(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"message": f"Session '{session_id}' cleared.", "session_id": session_id}

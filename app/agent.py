"""
Gemini Agent — the core reasoning engine that uses Google Generative AI
to perform risk assessment (Part 1) and conversational Q&A (Part 2).
"""

import json
import logging
from typing import Optional

import google.generativeai as genai

from app.config import GOOGLE_API_KEY, GEMINI_MODEL, TOP_K_DEFAULT
from app.prompts import RISK_ASSESSMENT_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from app.patient_service import get_patient
from app.vector_store import search_guidelines

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configure Gemini
# ---------------------------------------------------------------------------
genai.configure(api_key=GOOGLE_API_KEY)


def _build_context_from_chunks(chunks: list[dict]) -> str:
    """Format retrieved guideline chunks into a readable context block."""
    if not chunks:
        return "No relevant guideline sections were retrieved."

    sections = []
    for i, chunk in enumerate(chunks, 1):
        sections.append(
            f"--- Retrieved Section {i} [Page {chunk['page']}, "
            f"Chunk ID: {chunk['chunk_id']}] ---\n{chunk['text']}"
        )
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Part 1: Risk Assessment
# ---------------------------------------------------------------------------

def assess_patient(patient_id: str, top_k: int = TOP_K_DEFAULT) -> dict:
    """
    Full risk assessment pipeline:
    1. Retrieve patient data (tool use)
    2. Search vector store for relevant NG12 sections (RAG)
    3. Gemini reasons over both to produce structured assessment
    """
    # Step 1: Tool use — fetch patient record
    patient = get_patient(patient_id)
    if patient is None:
        return {
            "error": f"Patient '{patient_id}' not found.",
            "available_ids": "PT-101 through PT-110",
        }

    logger.info(f"Assessing patient {patient_id}: {patient['name']}")

    # Step 2: RAG — build search queries from patient symptoms
    symptom_queries = []
    for symptom in patient["symptoms"]:
        # Query with symptom + age context for better retrieval
        query = f"{symptom} age {patient['age']} {patient['gender']}"
        symptom_queries.append(query)

    # Also search for the symptom alone and with smoking context
    if patient.get("smoking_history") in ("Current Smoker", "Ex-Smoker"):
        for symptom in patient["symptoms"]:
            symptom_queries.append(f"{symptom} smoking smoker")

    # Deduplicate and search
    all_chunks = []
    seen_chunk_ids = set()
    for query in symptom_queries:
        results = search_guidelines(query, top_k=top_k)
        for chunk in results:
            if chunk["chunk_id"] not in seen_chunk_ids:
                seen_chunk_ids.add(chunk["chunk_id"])
                all_chunks.append(chunk)

    # Sort by relevance score and take top results
    all_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = all_chunks[:top_k * 2]  # Allow more context for better reasoning

    context = _build_context_from_chunks(top_chunks)

    # Step 3: Reasoning — Gemini synthesizes assessment
    user_prompt = f"""## Patient Record
- **Patient ID**: {patient['patient_id']}
- **Name**: {patient['name']}
- **Age**: {patient['age']}
- **Gender**: {patient['gender']}
- **Smoking History**: {patient['smoking_history']}
- **Symptoms**: {', '.join(patient['symptoms'])}
- **Symptom Duration**: {patient['symptom_duration_days']} days

## Retrieved NG12 Guideline Sections
{context}

## Task
Assess this patient against the NICE NG12 guideline criteria. Determine the appropriate risk level and recommended action. Return your response as a valid JSON object following the exact schema specified in your instructions. Return ONLY the JSON object, no markdown fences or extra text."""

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=RISK_ASSESSMENT_SYSTEM_PROMPT,
    )

    response = model.generate_content(
        user_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,  # Low temperature for deterministic clinical reasoning
            max_output_tokens=4096,
        ),
    )

    # Parse the JSON response
    response_text = response.text.strip()

    # Clean markdown fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    try:
        assessment = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Gemini response as JSON: {response_text[:500]}")
        assessment = {
            "patient_id": patient_id,
            "patient_name": patient["name"],
            "risk_level": "PARSE_ERROR",
            "raw_response": response_text,
            "reasoning": "The model response could not be parsed as JSON. See raw_response.",
        }

    # Attach the retrieved chunks as metadata for transparency
    assessment["retrieved_chunks"] = [
        {
            "chunk_id": c["chunk_id"],
            "page": c["page"],
            "score": c["score"],
            "excerpt": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"],
        }
        for c in top_chunks[:5]
    ]

    return assessment


# ---------------------------------------------------------------------------
# Part 2: Conversational Chat
# ---------------------------------------------------------------------------

# In-memory session storage
_sessions: dict[str, list[dict]] = {}


def get_chat_history(session_id: str) -> list[dict]:
    """Retrieve conversation history for a session."""
    return _sessions.get(session_id, [])


def clear_chat_history(session_id: str) -> bool:
    """Clear conversation history for a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def chat(session_id: str, message: str, top_k: int = TOP_K_DEFAULT) -> dict:
    """
    Multi-turn conversational Q&A over the NG12 guidelines.
    Uses conversation history for context and RAG for grounding.
    """
    # Initialize session if new
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]

    # Build a search query that incorporates conversation context
    # For follow-ups, combine with recent context
    search_query = message
    if history:
        # Include the last exchange for context in the search query
        last_messages = history[-2:]  # Last user + assistant messages
        context_snippets = [m["content"][:100] for m in last_messages]
        search_query = f"{message} {' '.join(context_snippets)}"

    # RAG retrieval
    chunks = search_guidelines(search_query, top_k=top_k)
    context = _build_context_from_chunks(chunks)

    # Build conversation history for Gemini
    gemini_history = []
    for msg in history[-10:]:  # Keep last 10 messages for context window
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    # Create the current prompt with retrieved context
    user_prompt = f"""## Retrieved NG12 Guideline Sections
{context}

## User Question
{message}

Please answer the question based ONLY on the retrieved guideline sections above. Include specific recommendation numbers and page references as citations."""

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=CHAT_SYSTEM_PROMPT,
    )

    # Start chat with history
    chat_session = model.start_chat(history=gemini_history)
    response = chat_session.send_message(
        user_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )

    answer = response.text.strip()

    # Store in session history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})

    # Build citations from retrieved chunks
    citations = [
        {
            "source": "NG12 PDF",
            "page": c["page"],
            "chunk_id": c["chunk_id"],
            "excerpt": c["text"][:300] + "..." if len(c["text"]) > 300 else c["text"],
            "relevance_score": c["score"],
        }
        for c in chunks
    ]

    return {
        "session_id": session_id,
        "answer": answer,
        "citations": citations,
    }
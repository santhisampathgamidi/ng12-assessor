"""Agent logic for risk assessment and guideline chat."""

import json
import logging
from typing import Optional

import google.generativeai as genai

from app.config import GOOGLE_API_KEY, GEMINI_MODEL, TOP_K_DEFAULT
from app.prompts import RISK_ASSESSMENT_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from app.patient_service import get_patient
from app.vector_store import search_guidelines

logger = logging.getLogger(__name__)

# Configure Gemini once on import.
genai.configure(api_key=GOOGLE_API_KEY)


def _build_context_from_chunks(chunks: list[dict]) -> str:
    """Turn retrieved chunks into a plain-text context block."""
    if not chunks:
        return "No relevant guideline sections were retrieved."

    sections = []
    for i, chunk in enumerate(chunks, 1):
        sections.append(
            f"--- Retrieved Section {i} [Page {chunk['page']}, "
            f"Chunk ID: {chunk['chunk_id']}] ---\n{chunk['text']}"
        )
    return "\n\n".join(sections)


# Risk assessment flow

def assess_patient(patient_id: str, top_k: int = TOP_K_DEFAULT) -> dict:
    """Run patient lookup, retrieval, and model reasoning end-to-end."""
    # 1) Pull the patient record.
    patient = get_patient(patient_id)
    if patient is None:
        return {
            "error": f"Patient '{patient_id}' not found.",
            "available_ids": "PT-101 through PT-110",
        }

    logger.info(f"Assessing patient {patient_id}: {patient['name']}")

    # 2) Build retrieval queries from symptoms and demographics.
    symptom_queries = []
    for symptom in patient["symptoms"]:
        # Add age + sex context to improve retrieval precision.
        query = f"{symptom} age {patient['age']} {patient['gender']}"
        symptom_queries.append(query)

    # Add smoking-aware variants when history is relevant.
    if patient.get("smoking_history") in ("Current Smoker", "Ex-Smoker"):
        for symptom in patient["symptoms"]:
            symptom_queries.append(f"{symptom} smoking smoker")

    # Run retrieval and dedupe by chunk id.
    all_chunks = []
    seen_chunk_ids = set()
    for query in symptom_queries:
        results = search_guidelines(query, top_k=top_k)
        for chunk in results:
            if chunk["chunk_id"] not in seen_chunk_ids:
                seen_chunk_ids.add(chunk["chunk_id"])
                all_chunks.append(chunk)

    # Keep the strongest chunks and pass extra context to the model.
    all_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = all_chunks[:top_k * 2]  # Keep more than top_k for better grounding.

    context = _build_context_from_chunks(top_chunks)

    # 3) Ask Gemini for the structured assessment.
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
            temperature=0.1,  # Prefer consistent, low-variance output.
            max_output_tokens=4096,
        ),
    )

    # Parse model output as JSON.
    response_text = response.text.strip()

    # Strip accidental markdown fences.
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Drop any line that looks like a code fence.
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

    # Return a short trace of retrieved chunks for debugging/transparency.
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


# Chat flow

# Session memory stored in-process.
_sessions: dict[str, list[dict]] = {}


def get_chat_history(session_id: str) -> list[dict]:
    """Return chat history for a session id."""
    return _sessions.get(session_id, [])


def clear_chat_history(session_id: str) -> bool:
    """Delete chat history for a session id."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def chat(session_id: str, message: str, top_k: int = TOP_K_DEFAULT) -> dict:
    """Answer a question using RAG plus recent chat history."""
    # Create session state if needed.
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]

    # Blend the new question with recent context for follow-ups.
    search_query = message
    if history:
        # Use only the latest exchange to keep the query short.
        last_messages = history[-2:]  # Last user + assistant messages
        context_snippets = [m["content"][:100] for m in last_messages]
        search_query = f"{message} {' '.join(context_snippets)}"

    # Retrieve relevant guideline chunks.
    chunks = search_guidelines(search_query, top_k=top_k)
    context = _build_context_from_chunks(chunks)

    # Convert local history to Gemini chat format.
    gemini_history = []
    for msg in history[-10:]:  # Last 10 messages keeps context without bloating tokens.
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    # Current question plus retrieved evidence.
    user_prompt = f"""## Retrieved NG12 Guideline Sections
{context}

## User Question
{message}

Please answer the question based ONLY on the retrieved guideline sections above. Include specific recommendation numbers and page references as citations."""

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=CHAT_SYSTEM_PROMPT,
    )

    # Run response generation with prior turns.
    chat_session = model.start_chat(history=gemini_history)
    response = chat_session.send_message(
        user_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )

    answer = response.text.strip()

    # Save this round in memory.
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})

    # Expose retrieved chunk metadata as citations.
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

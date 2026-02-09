# PROMPTS.md — Prompt Engineering & LangGraph Orchestration Strategy

## Overview

This document explains the system prompt design and LangGraph orchestration for both the **Risk Assessment Agent** (Part 1) and **Conversational Chat Agent** (Part 2).

---

## LangGraph Architecture

### Why LangGraph?

LangGraph provides a structured, stateful graph-based orchestration framework that:
- Makes the clinical reasoning pipeline **explicit and debuggable** — each step is a visible node
- Enables **conditional routing** (e.g., skip to error output if patient not found)
- Provides a foundation for **streaming** and **human-in-the-loop** extensions
- Aligns with production AI agent patterns used in healthcare systems

### Assessment Graph

```
[retrieve_patient] → [search_guidelines] → [reason] → [format_output] → END
        │                                                      ↑
        └──────── (error: patient not found) ──────────────────┘
```

**Nodes:**
1. `retrieve_patient` — Tool use: fetches structured patient data from simulated database
2. `search_guidelines` — RAG: builds symptom-aware queries, searches ChromaDB vector store
3. `reason` — LLM reasoning: Gemini synthesizes risk assessment from patient data + retrieved guidelines
4. `format_output` — Attaches retrieved chunk metadata for transparency

**State:** `AssessmentState` TypedDict flows through the graph carrying patient data, search queries, retrieved chunks, context, and the final assessment.

**Conditional Edge:** If patient is not found in step 1, the graph skips directly to `format_output` with an error message.

### Chat Graph

```
[build_query] → [search] → [generate] → END
```

**Nodes:**
1. `build_query` — Augments user message with conversation history for context-aware retrieval
2. `search` — RAG: searches vector store, formats context and citations
3. `generate` — LLM: generates grounded answer with citations using conversation history

---

## Part 1: Risk Assessment System Prompt

### Design Principles

1. **Role-based framing** — Clinical decision support specialist, not a diagnosing doctor
2. **Explicit process** — 4-step clinical reasoning workflow
3. **Hard constraints** — Citation grounding, age precision, terminology definitions
4. **Structured output** — JSON schema enforced for deterministic parsing

### Critical Rules

- Only cite provided guideline sections (never fabricate recommendation numbers)
- Age threshold precision (44 ≠ "45 and over")
- Smoking history changes the symptom threshold for lung/mesothelioma
- Consider ALL possible cancer types per symptom

### Configuration: Temperature = 0.1

Clinical reasoning requires determinism. Low temperature minimizes output variability.

---

## Part 2: Chat System Prompt

### Grounding Strategy (3-Layer Defense)

1. **Retrieval grounding** — "Only make statements supported by the guideline text provided"
2. **Citation enforcement** — `[NG12 Rec X.X.X, p.XX]` format required
3. **Failure behavior** — Explicit refusal phrase when evidence is insufficient

### Multi-turn Handling

- Last 10 messages included as conversation history
- Follow-up queries augmented with previous exchange context before vector search
- Enables coherent follow-ups like "What about for younger patients?"

---

## RAG Pipeline Design

### Chunking: 1000 chars / 200 overlap
- NG12 recommendations are 100-300 chars; 1000-char chunks capture 2-4 related recommendations
- 200-char overlap prevents recommendations at chunk boundaries from splitting

### Search Strategy
- **Assessment:** Multiple queries per patient (symptom + age + gender + smoking context)
- **Chat:** Single query, augmented with conversation history for follow-ups
- Results deduplicated by chunk_id, sorted by relevance score

### Metadata
Each chunk retains: page number, chunk_id (`ng12_PPPP_CCCC`), source filename — enabling precise citations.

---

## Vertex AI / Google AI Compatibility

The system supports both backends via configuration:
- `USE_VERTEX_AI=false` → Google AI Studio (API key, default)
- `USE_VERTEX_AI=true` → Google Vertex AI (GCP project + ADC)

The architecture is **SDK-agnostic**: swapping backends requires only changing environment variables.

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

### Critical Rules Embedded

- Only cite provided guideline sections (never fabricate recommendation numbers)
- Age threshold precision (44 ≠ "45 and over")
- Smoking history changes the symptom threshold for lung/mesothelioma
- Consider ALL possible cancer types per symptom
- "Unexplained" and "persistent" have specific clinical definitions

### Configuration: Temperature = 0.1

Clinical reasoning requires determinism. Low temperature minimizes output variability while allowing structured reasoning.

---

## Part 2: Chat System Prompt — Clinical Consultation Format

### Design Philosophy

The chat prompt is designed to produce **structured clinical consultation responses** that mirror how a senior clinician would advise a colleague. Every response follows a consistent framework with clearly labeled sections.

### Response Framework (7 Sections)

| Section | Purpose | When to Include |
|---------|---------|-----------------|
| 🔑 **Key Answer** | Direct 2-3 sentence answer for busy clinicians | ALWAYS |
| 📋 **NG12 Criteria Breakdown** | Specific recommendations with citations | ALWAYS |
| 👥 **Age-Stratified Guidance** | How thresholds vary by age group | When age-dependent |
| ⚠️ **Risk Modifiers & Red Flags** | Smoking, symptom combos, duration | When applicable |
| 🔄 **Related Pathways** | Cross-references to other cancer types | When multiple apply |
| 🛡️ **Safety Netting** | Sub-threshold patient management | When relevant |
| 💡 **Clinical Pearl** | Practical insight from senior perspective | ALWAYS |

### Prompt Engineering Techniques Used

1. **Internal Chain-of-Thought** — The prompt includes a "thinking process" section that guides the model through structured reasoning before generating the response, without exposing it to the user.

2. **Few-Shot via Embedded Example** — A complete high-quality example answer is embedded directly in the system prompt, demonstrating the expected depth, structure, and citation format.

3. **Grounding Defense-in-Depth** — Five non-negotiable grounding rules prevent hallucination:
   - Every claim must be supported by retrieved context
   - Specific citation format enforced: `[NG12 Rec X.X.X, p.XX]`
   - Transparent insufficient-evidence handling
   - No fabrication of any clinical data
   - No hedging language ("I think", "probably") on guideline content

4. **Minimum Response Length** — 200-word minimum prevents thin, unhelpful answers while ensuring clinical thoroughness.

5. **Terminology Reference Table** — Precise NG12 terminology definitions embedded in the prompt ensure consistent use of clinical language (e.g., "consider" vs "offer/refer" distinction).

### Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| No hallucinated recommendations | "Every factual claim MUST be supported by retrieved text" |
| No invented thresholds | "NEVER fabricate recommendation numbers, age thresholds, or clinical criteria" |
| Insufficient evidence handling | Explicit partial-answer + transparency template |
| Multi-turn coherence | History-augmented search + conversation context |
| Citation quality | Chunk metadata (page, chunk_id) attached to every response |
| Clinical precision | "NEVER say 'I think' or 'probably' about guideline content" |

---

## RAG Pipeline Design

### Chunking Strategy: 1000 chars / 200 overlap
- NG12 recommendations are typically 100-300 characters
- 1000-char chunks capture 2-4 related recommendations with surrounding context
- 200-char overlap prevents recommendations at chunk boundaries from being split

### Search Strategy
- **Assessment:** Multiple queries per patient — one per symptom, augmented with age, gender, and smoking context
- **Chat:** Single query augmented with conversation history for coherent follow-ups
- Results deduplicated by chunk_id, sorted by relevance score, top-k returned

### Metadata Preservation
Each chunk retains: page number, chunk_id (`ng12_PPPP_CCCC`), source filename — enabling precise citation back to the original guideline document.

---

## Vertex AI / Google AI Compatibility

The system supports both backends via a single environment variable:
- `USE_VERTEX_AI=false` → Google AI Studio (API key authentication, default)
- `USE_VERTEX_AI=true` → Google Vertex AI (GCP project + Application Default Credentials)

The architecture is **SDK-agnostic**: the LangGraph pipeline, prompts, vector store, and API layer are identical regardless of backend. Only the model initialization changes.

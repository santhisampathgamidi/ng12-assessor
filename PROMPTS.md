# PROMPTS.md — Prompt Engineering Strategy

## Overview

This document explains the system prompt design for both the **Risk Assessment Agent** (Part 1) and the **Conversational Chat Agent** (Part 2). Both agents use Gemini 1.5 with carefully crafted prompts that enforce clinical accuracy, grounding, and structured output.

---

## Part 1: Risk Assessment System Prompt

### Design Philosophy

The risk assessment prompt follows a **structured clinical reasoning** pattern, mirroring how a GP would work through the NG12 guideline in practice:

1. **Role definition** — The model is positioned as a clinical decision support specialist, not a doctor making diagnoses. This framing keeps outputs advisory and grounded.

2. **Explicit process steps** — The prompt lays out a 4-step process (receive → consult → match → output) that mirrors the actual clinical workflow in the assessment's architecture diagram.

3. **Critical rules as hard constraints** — The most important guardrails are:
   - **"Only cite guideline sections provided in your context"** — prevents hallucination of recommendation numbers
   - **Age threshold precision** — explicitly states that a 44-year-old does NOT meet "aged 45 and over"
   - **Terminology definitions** — "unexplained" and "persistent" are defined per NG12's own glossary
   - **Smoking history awareness** — the prompt highlights that smoking status changes the symptom threshold for lung/mesothelioma referrals

4. **Structured JSON output** — The prompt specifies an exact JSON schema. This serves two purposes:
   - Enables deterministic parsing by the API layer
   - Forces the model to think through each field (risk level, reasoning, citations) systematically

### Key Prompt Decisions

| Decision | Rationale |
|----------|-----------|
| Temperature = 0.1 | Clinical reasoning requires determinism; low temperature reduces variability |
| Multi-query RAG | Each symptom gets its own vector search query, plus smoking-aware queries. This maximizes recall for multi-symptom patients |
| "Consider ALL possible cancer types" | NG12 maps symptoms to multiple cancers — the prompt prevents tunnel vision |
| JSON-only output instruction | Eliminates markdown wrappers and preamble that break parsing |

### Prompt Structure

```
[Role Definition]
→ Who you are, what guideline you use

[Process Steps]
→ 1. Receive patient data
→ 2. Consult retrieved NG12 sections
→ 3. Match against criteria
→ 4. Output structured assessment

[Critical Rules]
→ Citation grounding
→ Age threshold precision
→ Terminology definitions
→ Multi-cancer consideration

[Output Schema]
→ Exact JSON structure with all required fields
```

---

## Part 2: Chat System Prompt

### Design Philosophy

The chat prompt prioritizes **grounded conversational fluency** — the agent must be helpful and natural while never exceeding what the retrieved guideline text supports.

### Grounding Strategy

The core grounding mechanism is a 3-layer defense:

1. **Retrieval grounding** — The prompt states "Ground every answer in the retrieved context" and "Only make statements supported by the guideline text provided to you."

2. **Citation enforcement** — Every clinical pathway statement must include a recommendation number and page reference in `[NG12 Rec X.X.X, p.XX]` format.

3. **Failure behavior** — When evidence is insufficient, the model must explicitly say so with a specific phrased response, rather than speculating.

### Multi-turn Handling

For follow-up questions, the system uses two mechanisms:

1. **Conversation history** — The last 10 messages are passed to Gemini as chat history, enabling the model to understand references like "What about for younger patients?"

2. **Context-aware RAG queries** — Follow-up questions are augmented with context from the previous exchange before searching the vector store. This ensures the retrieval finds relevant chunks even when the follow-up is terse (e.g., "What about under 40?").

### Key Terminology Section

The prompt includes a terminology block defining NG12-specific terms:
- Suspected cancer pathway referral (28 days)
- Urgent (2 weeks)
- Very urgent (48 hours)
- Immediate (hours)
- Direct access, Safety netting, Unexplained, Persistent

This prevents the model from using these terms loosely or incorrectly.

### Prompt Structure

```
[Role Definition]
→ NG12 guidelines assistant for healthcare professionals

[Grounding Rules]
→ 1. Ground in retrieved context
→ 2. Cite specific recommendations
→ 3. Acknowledge insufficient evidence
→ 4. Never invent thresholds

[Citation Format]
→ [NG12 Rec X.X.X, p.XX]

[Terminology Definitions]
→ NG12-specific clinical terms
```

---

## RAG Pipeline Design

### Chunking Strategy

- **Chunk size: 1000 characters** with **200-character overlap**
- **Rationale**: NG12 recommendations are typically 100-300 characters, so 1000-char chunks capture 2-4 related recommendations with surrounding context. The 200-char overlap ensures recommendations at chunk boundaries aren't split.

### Search Strategy

**Part 1 (Assessment):**
- Multiple queries per patient: one per symptom + age/gender context
- Additional smoking-aware queries for smokers/ex-smokers
- Results deduplicated by chunk ID, sorted by relevance
- Top 2×k chunks used (more context = better clinical reasoning)

**Part 2 (Chat):**
- Single query from user message
- For follow-ups: query augmented with last exchange context
- Top k chunks (default 5)

### Metadata Preservation

Each chunk retains:
- `page`: 1-based PDF page number
- `chunk_id`: Unique identifier (`ng12_PPPP_CCCC`)
- `source`: PDF filename

This enables precise citation in both assessment and chat responses.

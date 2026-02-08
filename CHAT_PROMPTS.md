# CHAT_PROMPTS.md — Chat Agent Prompt & Grounding Strategy

## Chat System Prompt Design

### Goal
Enable multi-turn, citation-grounded Q&A over the NG12 guideline using the **same vector store** built in Part 1. The chat agent must:
- Answer only from retrieved evidence
- Cite specific recommendation numbers and pages
- Handle follow-up questions using conversation context
- Refuse gracefully when evidence is insufficient

---

## Grounding Architecture

```
User Question
    │
    ├─ (if follow-up) → Augment query with last exchange context
    │
    ▼
Vector Store Search (ChromaDB)
    │
    ▼
Top-k chunks with page numbers + chunk IDs
    │
    ▼
Gemini 1.5 with:
  - System prompt (grounding rules)
  - Conversation history (last 10 messages)
  - Retrieved chunks as context
    │
    ▼
Grounded answer with [NG12 Rec X.X.X, p.XX] citations
```

## Key Design Decisions

### 1. Context-Aware Retrieval

For follow-up questions like "What about under 40?", the raw question alone wouldn't retrieve useful chunks. The system concatenates the user's message with snippets from the last exchange before searching:

```python
search_query = f"{message} {' '.join(context_snippets)}"
```

This ensures the vector search understands the topic being discussed.

### 2. Session Memory (In-Memory)

Conversation state is stored in a Python dictionary keyed by `session_id`:
- **Acceptable for the take-home** per the assessment requirements
- Each session stores a list of `{role, content}` messages
- Last 10 messages are sent to Gemini as chat history
- Sessions can be cleared via `DELETE /chat/{session_id}`

For production, this would be replaced by Redis or a database.

### 3. Failure Behavior

The system prompt explicitly instructs the model:

> "If the retrieved context does not contain sufficient information to answer the question, say: 'I couldn't find sufficient evidence in the NG12 guideline text to answer that question.'"

This is a hard guardrail — the model must not speculate beyond the retrieved evidence.

### 4. Citation Format

Inline citations use the format `[NG12 Rec X.X.X, p.XX]`:
- `X.X.X` = the NG12 recommendation number (e.g., 1.1.1)
- `p.XX` = the PDF page number from chunk metadata

The frontend highlights these citations with colored formatting.

## Example Interactions

### Basic Query
```
User: "What symptoms trigger an urgent referral for lung cancer?"
Agent: "According to NG12, a suspected cancer pathway referral for lung cancer
should be made if the patient has chest X-ray findings suggesting lung cancer,
or is aged 40+ with unexplained haemoptysis [NG12 Rec 1.1.1, p.9]. An urgent
chest X-ray should be offered to people aged 40+ with 2 or more unexplained
symptoms (cough, fatigue, shortness of breath, chest pain, weight loss,
appetite loss), or 1+ symptoms if they have ever smoked [NG12 Rec 1.1.2, p.9]."
```

### Follow-up
```
User: "What about for patients under 40?"
Agent: "The NG12 lung cancer recommendations specifically apply to people aged
40 and over [NG12 Rec 1.1.2, p.9]. For patients under 40, the guideline does
not provide specific lung cancer referral criteria based on these symptoms.
However, clinical judgement should always be applied, and safety netting should
be considered [NG12 Rec 1.15.2, p.35]."
```

### Insufficient Evidence
```
User: "What does NG12 say about genetic testing for cancer risk?"
Agent: "I couldn't find sufficient evidence in the NG12 guideline text to
answer that question. NG12 focuses on symptom-based recognition and referral
rather than genetic testing. You may want to consult other NICE guidelines
on familial cancer risk."
```

## Response Format

```json
{
  "session_id": "abc123",
  "answer": "According to NG12...",
  "citations": [
    {
      "source": "NG12 PDF",
      "page": 9,
      "chunk_id": "ng12_0009_0042",
      "excerpt": "Refer people using a suspected cancer pathway referral for lung cancer if they..."
    }
  ]
}
```

## Guardrails Checklist

| Guardrail | Implementation |
|-----------|---------------|
| No hallucinated recommendations | System prompt: "Only cite provided context" |
| No invented thresholds | System prompt: "Never invent thresholds or age criteria" |
| Insufficient evidence handling | Explicit refusal phrase in system prompt |
| Multi-turn coherence | Conversation history + context-augmented search |
| Citation quality | Chunk metadata (page, chunk_id) attached to every response |
| Reuse of Part 1 pipeline | Same ChromaDB instance, same embedding model |

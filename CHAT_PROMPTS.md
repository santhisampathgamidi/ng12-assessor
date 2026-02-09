# CHAT_PROMPTS.md — Chat Agent Grounding Strategy

## LangGraph Chat Pipeline

```
User Question
    │
    ▼
[build_query] — Augment with conversation history
    │
    ▼
[search] — ChromaDB vector search → top-k chunks
    │
    ▼
[generate] — Gemini + system prompt + history + chunks
    │
    ▼
Grounded answer with [NG12 Rec X.X.X, p.XX] citations
```

## Grounding Rules

1. Answer ONLY from retrieved guideline context
2. Cite with `[NG12 Rec X.X.X, p.XX]` inline
3. Say "I couldn't find sufficient evidence..." when retrieval returns irrelevant results
4. Never invent thresholds or recommendation numbers

## Multi-turn Coherence

- Conversation history (last 10 messages) sent to Gemini
- Follow-up search queries augmented with previous context
- Enables: "What about under 40?" → correctly scoped to the cancer type being discussed

## Failure Behavior

The model must refuse rather than speculate:
> "I couldn't find sufficient evidence in the NG12 guideline text to answer that question."

## Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| No hallucinated recommendations | System prompt: "Only cite provided context" |
| No invented thresholds | System prompt: "Never invent thresholds" |
| Insufficient evidence | Explicit refusal phrase |
| Multi-turn coherence | History + context-augmented search |
| Citation quality | Chunk metadata (page, chunk_id) per response |
| Reuse of Part 1 pipeline | Same ChromaDB, same embeddings |

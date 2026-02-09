# CHAT_PROMPTS.md — Chat Agent Grounding & Response Strategy

## LangGraph Chat Pipeline

```
User Question
    │
    ▼
[build_query] — Augment with conversation history for context-aware search
    │
    ▼
[search] — ChromaDB vector search → top-k relevant guideline chunks
    │
    ▼
[generate] — Gemini + structured system prompt + history + chunks
    │
    ▼
Structured clinical consultation response with [NG12 Rec X.X.X, p.XX] citations
```

## Response Structure — Clinical Consultation Format

Every chat response follows a structured framework inspired by how senior clinicians communicate:

| Section | Emoji | Purpose |
|---------|-------|---------|
| Key Answer | 🔑 | Direct answer in 2-3 sentences (always included) |
| NG12 Criteria Breakdown | 📋 | Specific recommendations with exact citations (always included) |
| Age-Stratified Guidance | 👥 | How criteria vary across age groups |
| Risk Modifiers & Red Flags | ⚠️ | Smoking, symptom combos, duration modifiers |
| Related Pathways | 🔄 | Cross-references to other cancer types |
| Safety Netting | 🛡️ | Sub-threshold patient management advice |
| Clinical Pearl | 💡 | Practical insight for clinical practice |

This structure ensures:
- **Scanability** — clinicians can jump to the section they need
- **Completeness** — nothing important is omitted
- **Consistency** — every answer follows the same format
- **Actionability** — clear recommendations, not vague commentary

## Grounding Strategy — 5-Layer Defense

| Layer | Rule | Purpose |
|-------|------|---------|
| 1 | Every claim must cite retrieved context | Prevents hallucination |
| 2 | Citation format: `[NG12 Rec X.X.X, p.XX]` | Enables verification |
| 3 | Explicit insufficient-evidence template | Prevents speculation |
| 4 | No fabrication of thresholds or numbers | Clinical safety |
| 5 | No hedging on guideline content | Authoritative responses |

## Prompt Engineering Techniques

### 1. Internal Chain-of-Thought
The system prompt includes a structured thinking process the model follows before generating:
- What is the user asking?
- Which retrieved sections are relevant?
- What are the precise thresholds?
- Are there multiple pathways?
- What would a senior GP need to act?

### 2. Few-Shot via Embedded Example
A complete high-quality answer is embedded in the prompt, demonstrating expected depth, structure, citation format, and clinical reasoning. This grounds the model's output quality.

### 3. Minimum Response Length
200-word minimum prevents thin answers. Clinical guidelines require thorough explanation — a one-line answer about cancer referral thresholds is never sufficient.

### 4. NG12 Terminology Table
Precise definitions embedded in prompt for terms like "consider" vs "offer/refer", "unexplained", "persistent", "safety netting" — ensures clinically accurate language.

## Multi-turn Coherence

- Last 10 messages included as conversation history in every Gemini call
- Follow-up search queries augmented with previous exchange context
- Enables coherent dialogue: "What about for younger patients?" → correctly scoped to the cancer type being discussed

## Failure Behavior

When retrieved context is insufficient, the model uses this template:
> "The guideline sections I have access to don't fully cover this. Based on what's available: [partial answer]. I'd recommend consulting the full NG12 guideline directly."

This is preferable to either:
- Fabricating an answer (dangerous in clinical context)
- Refusing to answer entirely (unhelpful)

## Pipeline Reuse

The chat agent reuses the **same ChromaDB vector store and embedding model** as the Part 1 assessment agent. This ensures:
- Consistent retrieval quality across both interfaces
- Single source of truth for guideline content
- No duplication of ingestion or storage

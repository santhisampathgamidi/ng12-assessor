# 🏥 NG12 Cancer Risk Assessor

An AI-powered clinical decision support system that assists healthcare professionals in cancer risk assessment and referral decisions based on NICE NG12 guidelines. Built with **LangGraph orchestration**, **Google Gemini 2.5 Flash**, and a **React** frontend.

> **Model Note:** This implementation uses Gemini 2.5 Flash (current production model) as Gemini 1.5 has been retired by Google. The system also supports **Google Vertex AI** — see [Switching to Vertex AI](#switching-to-vertex-ai).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              React + Vite + Tailwind CSS                    │
│         [Risk Assessment Tab]   [Chat Tab]                  │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
      POST /assess               POST /chat
           │                          │
┌──────────▼──────────────────────────▼───────────────────────┐
│                     FastAPI Backend                         │
│                                                             │
│   ┌─── LangGraph Assessment Graph ───────────────────┐      │
│   │  retrieve_patient → search_guidelines → reason   │      │
│   │        │ (error)          ↓              ↓       │      │
│   │        └──────→    format_output ← ──────┘       │      │
│   └──────────────────────────────────────────────────┘      │
│                                                             │
│   ┌─── LangGraph Chat Graph ────────────────────────┐       │
│   │  build_query → search → generate                │       │
│   │             (shared vector store)               │       │
│   └─────────────────────────────────────────────────┘       │
│                                                             │
│   [Patient DB]  [ChromaDB Vector Store]  [Gemini 2.5 Flash] │
│                                                             │
│        Configurable: Google AI Studio ←→ Vertex AI          │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google AI API key → [Get one free](https://aistudio.google.com/apikey)

### Option 1: Docker (Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env → add your GOOGLE_API_KEY

# 2. Place the NG12 PDF in data/
# Download from: https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621

# 3. Run setup (builds, starts, and ingests PDF)
chmod +x setup.sh
./setup.sh
```

Visit **http://localhost:8000**

### Option 2: Local Development

**Terminal 1 — Backend:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # Add your GOOGLE_API_KEY
python -m scripts.ingest_pdf --force   # ~5 min (rate limit pauses)
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173**

---

## Switching to Vertex AI

The system supports both **Google AI Studio** (default, API key) and **Google Vertex AI** (enterprise, GCP project). The architecture is SDK-agnostic — both use the same Gemini models and the same LangGraph pipeline. Only the authentication layer changes.

**To switch to Vertex AI:**

```bash
# In .env:
USE_VERTEX_AI=true
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1

# Authenticate:
gcloud auth application-default login
```

| Feature | Google AI Studio | Vertex AI |
|---------|-----------------|-----------|
| Authentication | API key | GCP IAM + ADC |
| Rate limits | Free tier (100 req/min) | Project quotas |
| Enterprise features | — | VPC, logging, compliance |
| Setup complexity | 1 minute | GCP project required |
| Models available | Same Gemini models | Same Gemini models |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/patients` | List all test patients |
| `POST` | `/assess` | Run LangGraph risk assessment |
| `POST` | `/chat` | Chat with NG12 guidelines |
| `GET` | `/chat/{session_id}/history` | Get conversation history |
| `DELETE` | `/chat/{session_id}` | Clear a chat session |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger API documentation |

**Example:**
```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "PT-101"}'
```

---

## Project Structure

```
ng12-assessor/
├── app/
│   ├── main.py              # FastAPI + frontend serving
│   ├── agent.py             # LangGraph graphs (assessment + chat)
│   ├── config.py            # Config (Vertex AI / Google AI toggle)
│   ├── models.py            # Pydantic request/response schemas
│   ├── prompts.py           # System prompts (assessment + chat)
│   ├── patient_service.py   # Simulated patient database
│   └── vector_store.py      # PDF ingestion + ChromaDB + embeddings
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app with tab navigation
│   │   └── components/
│   │       ├── AssessmentTab.jsx   # Risk assessment UI
│   │       └── ChatTab.jsx         # Guideline chat UI
│   ├── package.json
│   ├── vite.config.js       # Vite + API proxy config
│   └── tailwind.config.js
├── scripts/
│   └── ingest_pdf.py        # PDF → chunks → embeddings → ChromaDB
├── data/
│   └── patients.json        # 10 test patients (PT-101 to PT-110)
├── Dockerfile               # Multi-stage build (Node + Python)
├── docker-compose.yml
├── setup.sh                 # One-command Docker setup
├── requirements.txt
├── PROMPTS.md               # Prompt engineering documentation
├── CHAT_PROMPTS.md          # Chat grounding strategy
└── .env.example             # Environment template
```

---

## Key Design Decisions

### LangGraph Orchestration
Each pipeline step is an explicit graph node with typed state. This makes the clinical reasoning process transparent, debuggable, and extensible — critical for healthcare applications where auditability matters.

**Assessment graph:** `retrieve_patient → search_guidelines → reason → format_output`
- Conditional edge: skips to error output if patient not found
- Multiple symptom-aware search queries per patient

**Chat graph:** `build_query → search → generate`
- Reuses the same ChromaDB vector store as assessment
- History-augmented queries for multi-turn coherence

### Prompt Engineering
The chat prompt uses a **structured clinical consultation format** with 7 labeled sections (🔑 Key Answer, 📋 Criteria Breakdown, 👥 Age Guidance, ⚠️ Risk Modifiers, 🔄 Related Pathways, 🛡️ Safety Netting, 💡 Clinical Pearl). This ensures thorough, actionable responses. See [PROMPTS.md](PROMPTS.md) for full documentation.

### Gemini 2.5 Flash vs 1.5
Gemini 1.5 has been retired by Google. Gemini 2.5 Flash is the current production model with improved reasoning — beneficial for clinical decision support accuracy.

### In-Memory Chat Sessions
Chat history stored in Python dicts for simplicity. Production deployment would use Redis or PostgreSQL.

---

## Test Patients

| ID | Patient | Profile | Expected Outcome |
|----|---------|---------|-----------------|
| PT-101 | John Doe | 55M, smoker, hemoptysis | URGENT_REFERRAL — lung cancer |
| PT-102 | Jane Smith | 25F, cough 5 days | LOW_RISK — short duration |
| PT-103 | Robert Brown | 45M, ex-smoker, cough 28d | URGENT_INVESTIGATION — persistent |
| PT-104 | Sarah Connor | 35F, dysphagia 21d | URGENT_REFERRAL — oesophageal |
| PT-105 | Michael Chang | 65M, iron-deficiency anaemia | URGENT_REFERRAL — colorectal |
| PT-106 | Emily Blunt | 18F, fatigue only | SAFETY_NETTING — low risk |
| PT-107 | David Bowie | 48M, smoker, hoarseness 45d | URGENT_REFERRAL — laryngeal |
| PT-108 | Alice Wonderland | 32F, breast lump | URGENT_REFERRAL — breast |
| PT-109 | Tom Cruise | 45M, dyspepsia 7d | LOW_RISK — under threshold |
| PT-110 | Bruce Wayne | 60M, visible haematuria | URGENT_REFERRAL — bladder/renal |

---

## Future Improvements

- **Server-Sent Events** for real-time token streaming
- **Hybrid retrieval** (vector + BM25) for improved recall
- **Automated evaluation harness** for all 10 test patients
- **Redis/PostgreSQL** for persistent session storage
- **LangGraph streaming callbacks** for step-by-step UI progress

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | LangGraph (StateGraph) |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | Gemini Embedding 001 / Vertex AI text-embedding-004 |
| Vector DB | ChromaDB (persistent local) |
| Backend | FastAPI + Python 3.11 |
| Frontend | React 18 + Vite + Tailwind CSS |
| Containerization | Docker (multi-stage) |

# 🏥 NG12 Cancer Risk Assessor

A Clinical Decision Support Agent powered by **Google Gemini 1.5** and **NICE NG12 Guidelines** for suspected cancer recognition and referral.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (HTML/JS)                │
│          [Risk Assessment Tab] [Chat Tab]            │
└─────────────┬───────────────────────┬───────────────┘
              │                       │
         POST /assess            POST /chat
              │                       │
┌─────────────▼───────────────────────▼───────────────┐
│                  FastAPI Service                      │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Patient      │  │ Vector Store │  │ Gemini     │ │
│  │ Service      │  │ (ChromaDB)   │  │ Agent      │ │
│  │              │  │              │  │            │ │
│  │ patients.json│  │ NG12 PDF     │  │ Reasoning  │ │
│  │ → lookup     │  │ → embeddings │  │ + Citations│ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Features

### Part 1: Risk Assessment
- Accepts a Patient ID, retrieves structured records
- RAG retrieval of relevant NG12 guideline sections from ChromaDB
- Gemini 1.5 synthesizes a risk assessment with:
  - Risk level (URGENT_REFERRAL / URGENT_INVESTIGATION / VERY_URGENT / SAFETY_NETTING / LOW_RISK)
  - Recommended clinical action
  - Suspected cancer types
  - Step-by-step reasoning
  - Specific NG12 recommendation citations

### Part 2: Conversational Chat
- Multi-turn Q&A over the same NG12 vector store
- Session-based conversation memory
- Grounded answers with inline citations `[NG12 Rec X.X.X, p.XX]`
- Graceful handling of insufficient evidence
- Citation sources displayed per message

## Quick Start

### Prerequisites
- Python 3.11+
- A [Google AI API key](https://aistudio.google.com/apikey) (free tier works)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd ng12-assessor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Download the NG12 PDF

Download the guideline PDF and place it in the `data/` directory:

```bash
# The PDF should be at: data/suspected-cancer-recognition-and-referral-pdf-1837268071621.pdf
# Download from: https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621
```

### 4. Build the Vector Store

```bash
python -m scripts.ingest_pdf --stats
```

This parses the PDF, creates embeddings via Google AI, and stores them in ChromaDB.

### 5. Run the Service

```bash
uvicorn app.main:app --reload --port 8000
```

Visit: **http://localhost:8000**

## Running with Docker

```bash
# Build
docker build -t ng12-assessor .

# Run (pass your API key)
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your-key-here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/chroma_db:/app/chroma_db \
  ng12-assessor

# First time: ingest the PDF
docker exec <container-id> python -m scripts.ingest_pdf
```

Or with docker-compose:

```bash
# Set your API key in .env
echo "GOOGLE_API_KEY=your-key-here" > .env

docker-compose up --build
```

## API Endpoints

### Risk Assessment (Part 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/patients` | List all available patients |
| POST | `/assess` | Assess a patient against NG12 |
| GET | `/health` | Service health check |

**POST /assess**
```json
{ "patient_id": "PT-101" }
```

### Chat (Part 2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send a chat message |
| GET | `/chat/{session_id}/history` | Get conversation history |
| DELETE | `/chat/{session_id}` | Clear a session |

**POST /chat**
```json
{
  "session_id": "my-session",
  "message": "What symptoms trigger an urgent referral for lung cancer?",
  "top_k": 5
}
```

## Project Structure

```
ng12-assessor/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI application + endpoints
│   ├── config.py           # Environment configuration
│   ├── models.py           # Pydantic request/response schemas
│   ├── agent.py            # Gemini agent (assessment + chat)
│   ├── prompts.py          # System prompts for both agents
│   ├── patient_service.py  # Patient data retrieval (simulated DB)
│   └── vector_store.py     # PDF ingestion + ChromaDB + search
├── scripts/
│   └── ingest_pdf.py       # Standalone PDF ingestion script
├── frontend/
│   └── index.html          # Minimal UI (Assessment + Chat tabs)
├── data/
│   ├── patients.json       # Simulated patient database
│   └── *.pdf               # NG12 guideline PDF (you download this)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── PROMPTS.md              # Prompt engineering documentation
├── CHAT_PROMPTS.md         # Chat-specific grounding strategy
├── .env.example
├── .gitignore
└── README.md
```

## Prompt Engineering

See [PROMPTS.md](PROMPTS.md) for the risk assessment prompt strategy and [CHAT_PROMPTS.md](CHAT_PROMPTS.md) for the chat grounding approach.

## Test Patients

| ID | Name | Key Features | Expected Outcome |
|----|------|-------------|-----------------|
| PT-101 | John Doe | 55M, smoker, haemoptysis | **URGENT_REFERRAL** — lung cancer pathway |
| PT-102 | Jane Smith | 25F, cough 5 days | **LOW_RISK** — young, short duration, non-smoker |
| PT-103 | Robert Brown | 45M, ex-smoker, cough + SOB 28d | **URGENT_INVESTIGATION** — chest X-ray |
| PT-104 | Sarah Connor | 35F, dysphagia 21d | **URGENT_REFERRAL** — oesophageal/stomach |
| PT-105 | Michael Chang | 65M, iron-deficiency anaemia | **URGENT_INVESTIGATION** — FIT for colorectal |
| PT-106 | Emily Blunt | 18F, fatigue only | **SAFETY_NETTING** — low risk, monitor |
| PT-107 | David Bowie | 48M, smoker, hoarseness 45d | **URGENT_REFERRAL** — laryngeal cancer |
| PT-108 | Alice Wonderland | 32F, breast lump | **URGENT_REFERRAL** — breast cancer pathway |
| PT-109 | Tom Cruise | 45M, dyspepsia 7d | **LOW_RISK** — under 55, short duration |
| PT-110 | Bruce Wayne | 60M, visible haematuria | **URGENT_REFERRAL** — bladder/renal cancer |

## Technology Stack

- **LLM**: Google Gemini 1.5 (via `google-generativeai`)
- **Embeddings**: Google Generative AI Embeddings (`models/embedding-001`)
- **Vector DB**: ChromaDB (local persistent storage)
- **API Framework**: FastAPI
- **PDF Parsing**: pypdf
- **Text Splitting**: LangChain RecursiveCharacterTextSplitter
- **Containerization**: Docker

## License

This project is for assessment purposes. The NICE NG12 guideline content is © NICE 2026.

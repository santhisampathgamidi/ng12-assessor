# NG12 Cancer Risk Assessment System

> An intelligent clinical decision support tool leveraging AI-powered orchestration to assist healthcare professionals in cancer risk assessment and referral decisions based on NICE NG12 guidelines.

---

## 📋 Overview

This application provides healthcare professionals with an AI-assisted decision support system for suspected cancer recognition and referral. Built with modern technologies and clinical best practices, it combines LangGraph orchestration, Google Gemini AI, and NICE NG12 guidelines to deliver accurate, evidence-based risk assessments.

### Core Capabilities

- **Intelligent Risk Assessment**: Automated patient evaluation using clinical guidelines
- **Interactive Chat Interface**: Natural language queries about NG12 guidelines
- **Evidence-Based Recommendations**: Responses grounded in official NICE documentation
- **Dual Deployment Options**: Support for both Google AI Studio and Vertex AI

---

## 🏗️ System Architecture

The application follows a modular, microservices-inspired design with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│          React + Vite + Tailwind CSS                        │
│     [Risk Assessment Interface] | [Guideline Chat]          │
└────────────────┬────────────────────────┬───────────────────┘
                 │                        │
            POST /assess             POST /chat
                 │                        │
┌────────────────▼────────────────────────▼───────────────────┐
│                   Backend API Layer                         │
│                    (FastAPI)                                │
│                                                             │
│  ┌───────────────────────────────────────────────────┐      │
│  │        Assessment Workflow (LangGraph)            │      │
│  │                                                   │      │
│  │  Patient Retrieval ──→ Guideline Search           │      │
│  │        ↓                      ↓                   │      │
│  │   Patient DB            Vector Store              │      │
│  │  (JSON-based)          (ChromaDB)                 │      │
│  │                              ↓                    │      │
│  │                    Clinical Reasoning             │      │
│  │                      (Gemini AI)                  │      │
│  │                              ↓                    │      │
│  │                    Output Formatting              │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  ┌───────────────────────────────────────────────────┐      │
│  │         Chat Workflow (LangGraph)                 │      │
│  │                                                   │      │
│  │  Query Processing ──→ Search ──→ Response Gen     │      │
│  │                   (Shared Vector Store)           │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│           AI Backend: Vertex AI / Google AI Studio          │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### LangGraph-Based Orchestration
The system uses explicit state management through LangGraph, making each step of the clinical reasoning process:
- **Transparent**: Clear visibility into decision-making logic
- **Debuggable**: Easy to trace and troubleshoot
- **Extensible**: Simple to add new nodes (e.g., human review steps)

### Flexible AI Deployment
Switch seamlessly between deployment modes via environment configuration:
- **Google AI Studio**: Rapid prototyping with free tier
- **Vertex AI**: Enterprise-grade deployment with enhanced security and compliance

### Modern Frontend Experience
- Responsive design with Tailwind CSS
- Real-time typewriter effects for engaging user experience
- Intuitive tab-based navigation between assessment and chat modes

### Clinical-Grade Data Processing
- Vector embeddings of complete NICE NG12 guideline
- Semantic search for relevant clinical recommendations
- Context-aware response generation

---

## 🚀 Getting Started

### System Requirements

Ensure your development environment meets these prerequisites:

- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher
- **API Access**: Google AI API key ([obtain here](https://aistudio.google.com/apikey))

### Installation Guide

#### Step 1: Backend Configuration

```bash
# Navigate to project directory
cd ng12-assessor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env file and add your GOOGLE_API_KEY

# Download NICE NG12 PDF
# Source: https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621
# Place in: data/ng12.pdf

# Initialize vector database
python -m scripts.ingest_pdf --force

# Launch backend server
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`

#### Step 2: Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Access the application at: `http://localhost:5173`

### Advanced Configuration: Vertex AI

For production deployments with enhanced enterprise features:

```bash
# Update .env configuration
USE_VERTEX_AI=true
GCP_PROJECT_ID=your-google-cloud-project
GCP_LOCATION=us-central1

# Authenticate with Google Cloud
gcloud auth application-default login
```

---

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the Docker image
docker build -t ng12-assessor .

# Run container
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_api_key_here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/chroma_db:/app/chroma_db \
  ng12-assessor

# First-time setup: Initialize vector store
docker exec <container_id> python -m scripts.ingest_pdf
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 📚 API Reference

| HTTP Method | Endpoint | Purpose | Request Body |
|-------------|----------|---------|--------------|
| `GET` | `/patients` | Retrieve patient list | None |
| `POST` | `/assess` | Perform risk assessment | `{"patient_id": "string"}` |
| `POST` | `/chat` | Query guidelines | `{"message": "string", "session_id": "string"}` |
| `GET` | `/chat/{session_id}/history` | Retrieve chat history | None |
| `DELETE` | `/chat/{session_id}` | Clear conversation | None |

### Example Usage

```bash
# Assess a patient
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "P001"}'

# Chat with guidelines
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the criteria for lung cancer referral?", "session_id": "session123"}'
```

---

## 📁 Project Structure

```
ng12-assessor/
│
├── app/                          # Backend application code
│   ├── main.py                   # FastAPI application & route handlers
│   ├── agent.py                  # LangGraph workflow definitions
│   ├── config.py                 # Configuration management
│   ├── models.py                 # Data models (Pydantic schemas)
│   ├── prompts.py                # LLM prompt templates
│   ├── patient_service.py        # Patient data access layer
│   └── vector_store.py           # Vector database operations
│
├── frontend/                     # React application
│   ├── src/
│   │   ├── App.jsx               # Root component with routing
│   │   ├── components/
│   │   │   ├── AssessmentTab.jsx # Risk assessment interface
│   │   │   └── ChatTab.jsx       # Guideline chat interface
│   │   ├── main.jsx              # Application entry point
│   │   └── index.css             # Global styles
│   ├── package.json              # Node dependencies
│   ├── vite.config.js            # Vite bundler config
│   └── tailwind.config.js        # Tailwind CSS config
│
├── scripts/                      # Utility scripts
│   └── ingest_pdf.py             # PDF processing & embedding
│
├── data/                         # Data storage
│   ├── patients.json             # Patient records (simulated)
│   └── ng12.pdf                  # NICE guideline document
│
├── chroma_db/                    # Vector database storage
│
├── Dockerfile                    # Multi-stage container build
├── docker-compose.yml            # Service orchestration
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── PROMPTS.md                    # Prompt engineering documentation
├── CHAT_PROMPTS.md               # Chat-specific prompts
└── README.md                     # This file
```

---

## 🎯 Design Philosophy

### Orchestration-First Architecture
LangGraph provides explicit state machines for clinical workflows. Each node represents a discrete step in the reasoning process, making the system:
- **Auditable**: Full visibility into decision paths
- **Testable**: Individual components can be validated independently
- **Maintainable**: Clear separation makes updates straightforward

### Deployment Flexibility
The abstraction layer between Google AI Studio and Vertex AI allows teams to:
- Prototype rapidly with free-tier APIs
- Graduate to enterprise infrastructure seamlessly
- Maintain consistent behavior across environments

### Session Management
Current implementation uses in-memory storage for chat sessions. This design choice prioritizes:
- Development simplicity
- Low operational overhead
- Clear upgrade path to persistent storage

### Future Enhancements

Given additional development time, priority improvements would include:

1. **Streaming Responses**: Implement Server-Sent Events for real-time token streaming
2. **Hybrid Retrieval**: Combine vector search with BM25 for improved recall
3. **Automated Testing**: Evaluation harness covering all test patient scenarios
4. **Persistent Storage**: Redis integration for production-grade session management
5. **Workflow Observability**: LangGraph streaming callbacks for step-by-step UI updates
6. **Multi-Modal Support**: Integration of imaging data for comprehensive assessments

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | LangGraph (StateGraph) | Workflow management |
| **LLM** | Google Gemini 2.5 Flash | Clinical reasoning |
| **Embeddings** | Gemini Embedding 001 / text-embedding-004 | Semantic search |
| **Vector DB** | ChromaDB | Guideline storage & retrieval |
| **Backend** | FastAPI | API server |
| **Frontend** | React + Vite | User interface |
| **Styling** | Tailwind CSS | UI components |
| **Deployment** | Docker (multi-stage) | Containerization |

---

## 📝 Development Notes

### Environment Variables

Required configuration in `.env`:

```bash
# Required
GOOGLE_API_KEY=your_google_ai_api_key

# Optional (for Vertex AI)
USE_VERTEX_AI=false
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1

# Application
API_PORT=8000
FRONTEND_URL=http://localhost:5173
```

### Testing the System

```bash
# Run backend tests
pytest

# Test specific module
pytest tests/test_agent.py -v

# Frontend tests
cd frontend
npm test
```

---

## 📄 License

This project is intended for educational and research purposes. Clinical use requires appropriate validation and regulatory compliance.

---

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows existing style conventions
- Tests are included for new features
- Documentation is updated accordingly
- Commit messages are descriptive

---

## 📞 Support

For issues, questions, or contributions:
- Open an issue on the repository
- Review existing documentation in `/docs`
- Check the troubleshooting guide

---

**Built with modern AI orchestration for better clinical decision support**

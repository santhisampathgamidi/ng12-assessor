#!/bin/bash
# Starts containers and ingests the NG12 PDF once.

echo "🚀 Starting NG12 Cancer Risk Assessor Setup..."

# Make sure local env vars exist before booting anything.
if [ ! -f .env ]; then
    echo "⚠️  Error: .env file not found! Please create it from .env.example."
    exit 1
fi

# Build and start the stack.
echo "📦 Building and starting Docker containers..."
docker compose up -d --build

# Give the API a few seconds to come up.
echo "⏳ Waiting for the API service to initialize..."
sleep 15  # Uvicorn can take a moment on first start.

# Ingest the guideline PDF into Chroma.
echo "📖 Ingesting NG12 Guideline PDF into ChromaDB..."
docker exec -it ng12-cancer-risk-assessor python -m scripts.ingest_pdf

echo "✅ Setup Complete! Visit http://localhost:5173 to access the Assessor."

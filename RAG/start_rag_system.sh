#!/bin/bash

# Simple startup script for RAG-Report System
# Usage: ./RAG/start_rag_system.sh

echo "🚀 Starting RAG-Report Integration System"
echo "=========================================="

# Check if required directories exist
if [ ! -d "orchestrator" ]; then
    echo "❌ Error: orchestrator directory not found"
    exit 1
fi

if [ ! -d "RAG/ragAgent" ]; then
    echo "❌ Error: RAG/ragAgent directory not found"
    exit 1
fi

if [ ! -d "RAG/reportAgent" ]; then
    echo "❌ Error: RAG/reportAgent directory not found"
    exit 1
fi

echo "📁 All directories found"
echo ""

echo "🔧 Environment Variables:"
if [ -n "$GOOGLE_API_KEY" ]; then
    echo "  ✅ GOOGLE_API_KEY: Set"
else
    echo "  ⚠️  GOOGLE_API_KEY: Not set"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "  ✅ OPENAI_API_KEY: Set"
else
    echo "  ⚠️  OPENAI_API_KEY: Not set"
fi
echo ""

echo "🎯 To start the complete system, run these commands in separate terminals:"
echo ""
echo "Terminal 1 - Orchestrator:"
echo "  cd orchestrator && uv run -m app"
echo ""
echo "Terminal 2 - RAG Agent:"
echo "  cd RAG/ragAgent && uv run -m app"
echo ""
echo "Terminal 3 - Report Agent:"
echo "  cd RAG/reportAgent && uv run -m app"
echo ""
echo "📊 System will be available at:"
echo "  Orchestrator: http://localhost:8000"
echo "  RAG Agent: http://localhost:8004"
echo "  Report Agent: http://localhost:8003"
echo ""
echo "💡 Test the system with the orchestrator_client:"
echo "  cd orchestrator_client && uv run . --agent http://localhost:8000"

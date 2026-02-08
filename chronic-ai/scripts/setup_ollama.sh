#!/bin/bash
echo "🏥 Setting up Ollama models for ChronicAI..."

# Medical AI model
echo "📥 Pulling MedGemma 4B..."
ollama pull alibayram/medgemma:4b

# Verification model
echo "📥 Pulling Gemma 2B (instruct) for verification..."
ollama pull gemma:2b-instruct

# Embedding model
echo "📥 Pulling nomic-embed-text..."
ollama pull nomic-embed-text

echo "✅ All models ready!"
ollama list

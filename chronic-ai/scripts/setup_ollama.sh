#!/bin/bash
echo "🏥 Setting up Ollama models for ChronicAI..."

# Medical AI model
echo "📥 Pulling MedGemma 4B..."
ollama pull alibayram/medgemma:4b

# Translation model
echo "📥 Pulling Qwen 2.5 1.5B for translation..."
ollama pull qwen2.5:1.5b

# Embedding model
echo "📥 Pulling nomic-embed-text..."
ollama pull nomic-embed-text

echo "✅ All models ready!"
ollama list

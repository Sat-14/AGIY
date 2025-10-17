#!/bin/bash
# Setup Ollama for M1 Mac / Linux
# Ultra-lightweight LLM deployment for MacBook M1 8GB

echo "🍎 Setting up Ollama for M1 Mac / RTX 3060"
echo "=========================================="

# Install Ollama
echo "📦 Installing Ollama..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if ! command -v ollama &> /dev/null; then
        brew install ollama
    fi
else
    # Linux
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama service
echo "🚀 Starting Ollama service..."
ollama serve &
sleep 5

# Pull lightweight models
echo "⬇️  Pulling TinyLlama (1.1B) - 637MB..."
ollama pull tinyllama

echo "⬇️  Pulling StableLM 2 (1.6B) - 1.1GB..."
ollama pull stablelm2:1.6b

echo "✅ Model Installation Complete!"
echo ""
echo "📊 Installed Models:"
ollama list

echo ""
echo "🧪 Testing Recommendation Model (TinyLlama)..."
ollama run tinyllama "Recommend 2 jackets for casual style. Be brief." --

echo ""
echo "🧪 Testing Inventory Model (StableLM2)..."
ollama run stablelm2:1.6b "Check stock: SKU_JCK_01. Format: JSON" --

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📝 Next Steps:"
echo "  1. Run recommendation agent: python recommendation-agent/agent_local_llm.py"
echo "  2. Run inventory agent: python inventory-agent/agent_local_llm.py"
echo ""
echo "💡 Memory Usage:"
echo "  - TinyLlama: ~600MB VRAM"
echo "  - StableLM2: ~1.1GB VRAM"
echo "  - Total: ~1.7GB (leaves 6.3GB free on M1 8GB)"
echo ""
echo "🔥 Can run both models simultaneously on M1 8GB!"

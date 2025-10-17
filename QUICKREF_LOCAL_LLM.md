# Local LLM Quick Reference Card

## 🚀 **30-Second Setup (Ollama)**

```bash
# macOS/Linux
./local_llm/setup_ollama.sh
python recommendation-agent/agent_local_llm.py &
python inventory-agent/agent_local_llm.py &

# Windows
local_llm\setup_ollama.bat
python recommendation-agent\agent_local_llm.py
python inventory-agent\agent_local_llm.py
```

---

## 📊 **Memory Requirements**

| Device | Total Memory | Model 1 | Model 2 | Free |
|--------|--------------|---------|---------|------|
| **M1 8GB** | 8GB | 600MB | 1.1GB | 6.3GB |
| **RTX 3060** | 6GB | 1.5GB | 2.5GB | 2GB |

---

## 🤖 **Models Used**

### Recommendation Agent
- **M1:** TinyLlama 1.1B (600MB)
- **RTX:** Gemma 2B (1.5GB)

### Inventory Agent
- **M1:** StableLM 2 1.6B (1.1GB)
- **RTX:** Phi-3 Mini 3.8B (2.5GB)

---

## 🧪 **Test Commands**

```bash
# Test Ollama
ollama run tinyllama "Recommend jackets"
ollama run stablelm2:1.6b "Check stock"

# Test API
curl -X POST http://localhost:5002/get-recommendations \
  -d '{"user_id":"test","context":"jacket","count":3}'

curl -X POST http://localhost:5003/check-inventory \
  -d '{"product_id":"SKU_JCK_01"}'

# Submit Feedback
curl -X POST http://localhost:5002/feedback \
  -d '{"user_id":"test","recommendation_id":"SKU_X","rating":5}'
```

---

## 🔄 **Training**

```bash
# Manual training (after collecting feedback)
python local_llm/training_pipeline.py recommendation
python local_llm/training_pipeline.py inventory

# Auto-training triggers after:
# - 50-100 feedbacks collected
# - Runs automatically in background
# - Updates LoRA adapters (~30MB)
```

---

## 📈 **Performance**

| Metric | M1 8GB | RTX 3060 |
|--------|--------|----------|
| Inference | 40-50 tok/s | 70-80 tok/s |
| Training | 30 min | 15 min |
| Quality | 7-8/10 | 8-9/10 |

---

## 🔑 **Key Files**

- **Setup:** `local_llm/setup_ollama.*`
- **Agents:** `*-agent/agent_local_llm.py`
- **Training:** `local_llm/training_pipeline.py`
- **Config:** `local_llm/*_config.py`

---

## 💡 **Tips**

1. **Use Ollama** - Easiest for M1
2. **4-bit quantization** - Saves 75% memory
3. **QLoRA training** - Lightweight fine-tuning
4. **Batch size 1** - For M1 training
5. **Monitor feedback** - data/feedback/*.jsonl

---

## 📚 **Docs**

- Full Guide: [LOCAL_LLM_SETUP.md](LOCAL_LLM_SETUP.md)
- Summary: [LOCAL_LLM_SUMMARY.md](LOCAL_LLM_SUMMARY.md)
- Main: [README.md](README.md)

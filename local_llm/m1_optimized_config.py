"""
MacBook M1 8GB Optimized LLM Configuration
Ultra-lightweight models that can train and run on M1 with 8GB unified memory
"""

from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum

class M1OptimizedModel(Enum):
    """Ultra-lightweight models for M1 8GB"""
    TINYLLAMA_1B = "tinyllama-1.1b"      # 1.1B params - 600MB VRAM
    PHI_2 = "phi-2"                      # 2.7B params - 1.5GB VRAM
    GEMMA_2B = "gemma-2b"                # 2B params - 1GB VRAM
    QWEN_1_8B = "qwen-1.8b"             # 1.8B params - 900MB VRAM
    STABLELM_2 = "stablelm-2-1.6b"      # 1.6B params - 800MB VRAM

@dataclass
class M1LLMConfig:
    """Configuration optimized for M1 8GB"""
    model_name: str
    model_type: M1OptimizedModel
    quantization: str = "4bit"           # 4bit for M1
    max_tokens: int = 256
    temperature: float = 0.7
    max_memory_mb: int = 2000            # Max 2GB per model
    use_mps: bool = True                 # Use Metal Performance Shaders

    # Fine-tuning (extremely lightweight)
    use_qlora: bool = True               # QLoRA for 8GB systems
    lora_rank: int = 4                   # Lower rank for M1
    lora_alpha: int = 8
    lora_dropout: float = 0.05

    # Training config
    batch_size: int = 1
    gradient_accumulation_steps: int = 8
    max_grad_norm: float = 0.3
    learning_rate: float = 2e-4

    # Continuous improvement
    collect_feedback: bool = True
    retrain_threshold: int = 50          # Retrain after 50 feedbacks
    auto_optimize: bool = True           # Auto-optimize for M1


# M1 8GB Optimized Configurations (can run 2-3 models simultaneously)
M1_8GB_CONFIGS = {
    "recommendation": M1LLMConfig(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type=M1OptimizedModel.TINYLLAMA_1B,
        quantization="4bit",
        max_tokens=256,
        temperature=0.7,
        max_memory_mb=1500,  # 1.5GB max
    ),

    "inventory": M1LLMConfig(
        model_name="stabilityai/stablelm-2-1_6b",
        model_type=M1OptimizedModel.STABLELM_2,
        quantization="4bit",
        max_tokens=128,
        temperature=0.3,
        max_memory_mb=1200,  # 1.2GB max
    ),

    "fulfillment": M1LLMConfig(
        model_name="Qwen/Qwen-1_8B-Chat",
        model_type=M1OptimizedModel.QWEN_1_8B,
        quantization="4bit",
        max_tokens=256,
        temperature=0.4,
        max_memory_mb=900,  # 900MB max
    ),

    "loyalty": M1LLMConfig(
        model_name="microsoft/phi-2",
        model_type=M1OptimizedModel.PHI_2,
        quantization="4bit",
        max_tokens=200,
        temperature=0.3,
        max_memory_mb=1500,  # 1.5GB max
    ),

    "payment": M1LLMConfig(
        model_name="stabilityai/stablelm-2-1_6b",
        model_type=M1OptimizedModel.STABLELM_2,
        quantization="4bit",
        max_tokens=150,
        temperature=0.2,
        max_memory_mb=1000,  # 1GB max
    ),

    "post_purchase": M1LLMConfig(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type=M1OptimizedModel.TINYLLAMA_1B,
        quantization="4bit",
        max_tokens=256,
        temperature=0.6,
        max_memory_mb=800,  # 800MB max
    ),

    # Alternative ultra-lightweight option
    "ultra_light": M1LLMConfig(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type=M1OptimizedModel.TINYLLAMA_1B,
        quantization="4bit",
        max_tokens=128,
        max_memory_mb=800,   # 800MB max
    ),
}


# Ollama models optimized for M1
OLLAMA_M1_MODELS = {
    "recommendation": "tinyllama:1.1b",    # 637MB
    "inventory": "stablelm2:1.6b",         # 1.1GB
    "fulfillment": "qwen:1.8b",            # 1.1GB
    "loyalty": "phi:2.7b",                 # 1.7GB
    "payment": "stablelm2:1.6b",           # 1.1GB
    "post_purchase": "tinyllama:1.1b",     # 637MB
    "general": "phi:2.7b",                 # 1.7GB (if more memory available)
}


def get_m1_memory_estimate(config: M1LLMConfig) -> Dict[str, float]:
    """
    Estimate memory for M1 (unified memory system)

    Returns:
        Memory estimates in MB
    """
    base_sizes_mb = {
        M1OptimizedModel.TINYLLAMA_1B: 1100,   # 1.1GB
        M1OptimizedModel.PHI_2: 2700,          # 2.7GB
        M1OptimizedModel.GEMMA_2B: 2000,       # 2GB
        M1OptimizedModel.QWEN_1_8B: 1800,      # 1.8GB
        M1OptimizedModel.STABLELM_2: 1600,     # 1.6GB
    }

    base_size = base_sizes_mb.get(config.model_type, 1100)

    # 4-bit quantization reduces to ~25% of original
    if config.quantization == "4bit":
        model_size = base_size * 0.25
    elif config.quantization == "8bit":
        model_size = base_size * 0.5
    else:
        model_size = base_size

    # M1 specific overheads
    mps_overhead = 150      # Metal Performance Shaders
    inference_overhead = 200 # Inference buffers
    lora_size = 30 if config.use_qlora else 0  # QLoRA adapters

    total = model_size + mps_overhead + inference_overhead + lora_size

    # Training memory (if needed)
    training_overhead = 300 if config.use_qlora else 0
    training_total = total + training_overhead

    return {
        "model_size_mb": round(model_size, 1),
        "mps_overhead_mb": mps_overhead,
        "inference_overhead_mb": inference_overhead,
        "lora_adapters_mb": lora_size,
        "inference_total_mb": round(total, 1),
        "training_total_mb": round(training_total, 1),
        "fits_m1_8gb": training_total < 2500,  # Leave 5.5GB for system
        "can_run_multiple": total < 1500,      # Can run 2-3 simultaneously
    }


# M1-specific model prompts (more concise for smaller models)
M1_AGENT_PROMPTS = {
    "recommendation": """Product recommendations for fashion retail.
Customer: {context}
Preferences: {preferences}

Give 2-3 product suggestions with IDs. Format:
[{{"id": "SKU_X", "reason": "matches style"}}]""",

    "inventory": """Check stock for fashion retail.
Product: {query}
Location: {location}

Give stock status. Format:
{{"status": "in_stock|low|out", "qty": X, "stores": [...]}}""",

    "fulfillment": """Store reservation for fashion retail.
Product: {product_id}
Store: {store_id}
User: {user_id}

Validate and create reservation. Format:
{{"status": "success|error", "reservationId": "RES-XXX", "message": "..."}}""",

    "loyalty": """Calculate offers for fashion retail.
User Tier: {tier}
Cart Amount: {cart_amount}
Available Points: {loyalty_points}

Suggest best offers. Format:
{{"offers": [...], "points_value": X, "recommendations": [...]}}""",

    "payment": """Process payment for fashion retail.
Transaction: {transaction_id}
Amount: {amount}
Method: {payment_method}

Validate and process. Format:
{{"status": "success|failed", "message": "...", "suggestions": [...]}}""",

    "post_purchase": """Order support for fashion retail.
Order: {order_id}
Query: {query}

Provide status or handle return. Format:
{{"status": "...", "message": "...", "details": {{...}}}}""",
}


# Recommended deployment for M1 8GB
M1_DEPLOYMENT_STRATEGY = {
    "scenario_1": {
        "name": "Dual Model Setup (Recommended)",
        "models": ["recommendation", "inventory"],
        "total_memory_mb": 2700,  # ~2.7GB
        "remaining_memory_gb": 5.3,
        "description": "Run TinyLlama (recommendation) + StableLM (inventory)"
    },

    "scenario_2": {
        "name": "Ollama Setup (Easiest)",
        "models": ["tinyllama:1.1b", "stablelm2:1.6b"],
        "total_memory_mb": 1700,  # ~1.7GB
        "remaining_memory_gb": 6.3,
        "description": "Use Ollama with quantized models"
    },

    "scenario_3": {
        "name": "Ultra-Light Setup (3+ models)",
        "models": ["tinyllama"] * 3,
        "total_memory_mb": 2400,  # ~2.4GB
        "remaining_memory_gb": 5.6,
        "description": "Run 3 TinyLlama instances for different agents"
    },
}


def print_m1_deployment_guide():
    """Print M1 8GB deployment guide"""
    print("\n" + "="*70)
    print("MacBook M1 8GB Deployment Guide")
    print("="*70)

    print("\n📊 Recommended Models:")
    print("-" * 70)
    for agent, config in M1_8GB_CONFIGS.items():
        mem = get_m1_memory_estimate(config)
        print(f"\n{agent.upper()}:")
        print(f"  Model: {config.model_name}")
        print(f"  Size: {mem['model_size_mb']} MB (quantized)")
        print(f"  Inference: {mem['inference_total_mb']} MB")
        print(f"  Training: {mem['training_total_mb']} MB")
        print(f"  ✅ Can run multiple: {mem['can_run_multiple']}")

    print("\n\n🚀 Deployment Strategies:")
    print("-" * 70)
    for key, strategy in M1_DEPLOYMENT_STRATEGY.items():
        print(f"\n{strategy['name']}:")
        print(f"  Total Memory: {strategy['total_memory_mb']} MB")
        print(f"  Free Memory: {strategy['remaining_memory_gb']} GB")
        print(f"  Models: {', '.join(strategy['models'])}")
        print(f"  📝 {strategy['description']}")

    print("\n\n💡 Training on M1:")
    print("-" * 70)
    print("  • Use QLoRA (4-bit quantization + LoRA)")
    print("  • Batch size: 1")
    print("  • Gradient accumulation: 8 steps")
    print("  • Training memory: ~2GB per model")
    print("  • Can train 1 model at a time")
    print("  • Training time: ~30min for 100 samples")

    print("\n" + "="*70 + "\n")


# M1-specific optimization tips
M1_OPTIMIZATION_TIPS = """
🍎 M1 8GB Optimization Tips:

1. **Use Ollama (Recommended)**
   ```bash
   brew install ollama
   ollama pull tinyllama
   ollama pull stablelm2:1.6b
   ```

2. **Use 4-bit Quantization**
   - Reduces memory by 75%
   - Minimal quality loss
   - Enables multiple models

3. **Training Strategy**
   - Train 1 model at a time
   - Use QLoRA (not full fine-tuning)
   - Batch size = 1
   - Gradient accumulation = 8

4. **Memory Management**
   - Close other apps during training
   - Use swap space efficiently
   - Monitor with Activity Monitor

5. **Model Selection**
   - TinyLlama 1.1B: Best for M1
   - StableLM 1.6B: Good balance
   - Avoid models > 3B params
"""


if __name__ == "__main__":
    print_m1_deployment_guide()
    print(M1_OPTIMIZATION_TIPS)

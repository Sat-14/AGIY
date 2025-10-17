"""
Local LLM Configuration for RTX 3060 (6GB VRAM)
Supports lightweight models with continuous improvement via fine-tuning
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class ModelType(Enum):
    """Supported lightweight LLM types"""
    GEMMA_2B = "gemma-2b"           # Google's Gemma 2B (RTX 3060 friendly)
    PHI_3_MINI = "phi-3-mini"       # Microsoft Phi-3 Mini 3.8B
    LLAMA_3_8B = "llama-3-8b"       # Meta Llama 3 8B (quantized)
    MISTRAL_7B = "mistral-7b"       # Mistral 7B (quantized)
    TINYLLAMA = "tinyllama"         # TinyLlama 1.1B

@dataclass
class LLMConfig:
    """Configuration for local LLM"""
    model_name: str
    model_type: ModelType
    quantization: str = "4bit"      # 4bit, 8bit, or none
    max_tokens: int = 512
    temperature: float = 0.7
    gpu_memory_fraction: float = 0.8
    use_flash_attention: bool = True
    device: str = "cuda"

    # Fine-tuning config
    use_lora: bool = True
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05

    # Continuous improvement
    collect_feedback: bool = True
    retrain_threshold: int = 100    # Number of feedbacks before retraining
    feedback_db_path: str = "data/feedback"


# RTX 3060 Optimized Configurations
RTX_3060_CONFIGS = {
    "recommendation": LLMConfig(
        model_name="google/gemma-2b-it",
        model_type=ModelType.GEMMA_2B,
        quantization="4bit",
        max_tokens=384,
        temperature=0.7,
        gpu_memory_fraction=0.4,  # Use 40% VRAM (~2.4GB)
    ),

    "inventory": LLMConfig(
        model_name="microsoft/phi-3-mini-4k-instruct",
        model_type=ModelType.PHI_3_MINI,
        quantization="4bit",
        max_tokens=256,
        temperature=0.3,  # Lower for factual responses
        gpu_memory_fraction=0.4,  # Use 40% VRAM (~2.4GB)
    ),

    # Alternative lightweight options
    "tinyllama": LLMConfig(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type=ModelType.TINYLLAMA,
        quantization="8bit",
        max_tokens=512,
        gpu_memory_fraction=0.3,  # Use 30% VRAM (~1.8GB)
    ),
}


class ModelSelector:
    """Selects appropriate model based on VRAM availability"""

    @staticmethod
    def get_available_vram() -> float:
        """Get available GPU VRAM in GB"""
        try:
            import torch
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                total = torch.cuda.get_device_properties(device).total_memory / (1024**3)
                allocated = torch.cuda.memory_allocated(device) / (1024**3)
                return total - allocated
            return 0.0
        except:
            return 0.0

    @staticmethod
    def select_model_for_agent(agent_name: str, vram_gb: float = 6.0) -> LLMConfig:
        """
        Select model based on agent and available VRAM

        Args:
            agent_name: Name of the agent (recommendation, inventory, etc.)
            vram_gb: Available VRAM in GB (default 6GB for RTX 3060)

        Returns:
            LLMConfig for the agent
        """
        if agent_name in RTX_3060_CONFIGS:
            return RTX_3060_CONFIGS[agent_name]

        # Fallback based on VRAM
        if vram_gb >= 5:
            return RTX_3060_CONFIGS["inventory"]  # Phi-3 Mini
        elif vram_gb >= 3:
            return RTX_3060_CONFIGS["recommendation"]  # Gemma 2B
        else:
            return RTX_3060_CONFIGS["tinyllama"]  # TinyLlama 1.1B


# Model-specific prompts
AGENT_PROMPTS = {
    "recommendation": """You are a product recommendation specialist for ABFRL fashion retail.
Your task is to analyze customer preferences and suggest relevant products.

Guidelines:
- Focus on fashion trends and customer preferences
- Provide 2-3 concise product suggestions
- Include price and availability info
- Match customer's style preferences
- Be brief and direct

Customer Context: {context}
User Preferences: {preferences}

Provide recommendations in JSON format:
{{"recommendations": [{{"product_id": "...", "reason": "..."}}]}}""",

    "inventory": """You are an inventory specialist for ABFRL fashion retail.
Your task is to provide accurate stock information and availability.

Guidelines:
- Report exact stock levels
- Mention warehouse and store availability
- Indicate low stock warnings
- Provide fulfillment options
- Be precise and factual

Product Query: {query}
Location: {location}

Provide stock info in JSON format:
{{"stock_status": "...", "quantity": ..., "locations": [...]}}""",
}


def get_model_memory_estimate(config: LLMConfig) -> Dict[str, float]:
    """
    Estimate memory requirements for model

    Returns:
        Dict with memory estimates in GB
    """
    base_sizes = {
        ModelType.GEMMA_2B: 2.0,
        ModelType.PHI_3_MINI: 3.8,
        ModelType.LLAMA_3_8B: 8.0,
        ModelType.MISTRAL_7B: 7.0,
        ModelType.TINYLLAMA: 1.1,
    }

    base_size = base_sizes.get(config.model_type, 2.0)

    # Quantization reduces size
    if config.quantization == "4bit":
        model_size = base_size * 0.25
    elif config.quantization == "8bit":
        model_size = base_size * 0.5
    else:
        model_size = base_size

    # Add overhead for inference
    inference_overhead = 0.5  # GB

    # LoRA adapters (if used)
    lora_size = 0.1 if config.use_lora else 0.0

    total = model_size + inference_overhead + lora_size

    return {
        "model_size_gb": model_size,
        "inference_overhead_gb": inference_overhead,
        "lora_adapters_gb": lora_size,
        "total_estimated_gb": total,
        "fits_rtx_3060": total < 5.5  # Leave 0.5GB buffer
    }


# Model recommendations by use case
MODEL_RECOMMENDATIONS = {
    "recommendation_agent": {
        "primary": "gemma-2b",  # Best for text generation
        "alternative": "phi-3-mini",
        "reason": "Gemma 2B excels at creative product recommendations"
    },
    "inventory_agent": {
        "primary": "phi-3-mini",  # Best for factual responses
        "alternative": "tinyllama",
        "reason": "Phi-3 Mini is highly accurate for structured data"
    },
}


def print_model_info(config: LLMConfig):
    """Print model configuration and memory estimates"""
    print(f"\n{'='*60}")
    print(f"Model Configuration: {config.model_name}")
    print(f"{'='*60}")
    print(f"Type: {config.model_type.value}")
    print(f"Quantization: {config.quantization}")
    print(f"Max Tokens: {config.max_tokens}")
    print(f"Temperature: {config.temperature}")
    print(f"Use LoRA: {config.use_lora}")

    mem_info = get_model_memory_estimate(config)
    print(f"\nMemory Estimates:")
    print(f"  Model Size: {mem_info['model_size_gb']:.2f} GB")
    print(f"  Inference Overhead: {mem_info['inference_overhead_gb']:.2f} GB")
    print(f"  LoRA Adapters: {mem_info['lora_adapters_gb']:.2f} GB")
    print(f"  Total Estimated: {mem_info['total_estimated_gb']:.2f} GB")
    print(f"  Fits RTX 3060 (6GB): {'✅ YES' if mem_info['fits_rtx_3060'] else '❌ NO'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Test configurations
    for agent_name, config in RTX_3060_CONFIGS.items():
        print_model_info(config)

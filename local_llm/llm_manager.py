"""
Local LLM Manager with Continuous Improvement
Supports Ollama and HuggingFace Transformers
"""

import os
import json
import torch
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, PeftModel
import bitsandbytes as bnb

from local_llm.model_config import LLMConfig, AGENT_PROMPTS

logger = logging.getLogger(__name__)


class LocalLLMManager:
    """Manages local LLM with continuous improvement capabilities"""

    def __init__(self, config: LLMConfig, agent_name: str):
        self.config = config
        self.agent_name = agent_name
        self.model = None
        self.tokenizer = None
        self.peft_model = None
        self.feedback_data = []

        # Paths
        self.base_model_path = f"models/{agent_name}/base"
        self.lora_path = f"models/{agent_name}/lora"
        self.feedback_path = f"{config.feedback_db_path}/{agent_name}.jsonl"

        os.makedirs(os.path.dirname(self.feedback_path), exist_ok=True)

    def load_model(self):
        """Load model with quantization for RTX 3060"""
        logger.info(f"Loading {self.config.model_name} for {self.agent_name}")

        # Quantization config for 4-bit
        if self.config.quantization == "4bit":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        elif self.config.quantization == "8bit":
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True
            )
        else:
            quantization_config = None

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
        )

        # Load LoRA adapters if they exist
        if os.path.exists(self.lora_path):
            logger.info(f"Loading LoRA adapters from {self.lora_path}")
            self.model = PeftModel.from_pretrained(
                self.model,
                self.lora_path,
                is_trainable=False
            )

        logger.info(f"Model loaded successfully for {self.agent_name}")

    def generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response using local LLM"""
        if self.model is None:
            self.load_model()

        # Format prompt with agent-specific template
        agent_prompt = AGENT_PROMPTS.get(self.agent_name, "{context}\n{query}")
        formatted_prompt = agent_prompt.format(
            context=context.get("context", "") if context else "",
            query=prompt,
            preferences=context.get("preferences", "") if context else "",
            location=context.get("location", "") if context else ""
        )

        # Tokenize
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self.model.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        response = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )

        # Extract only the generated part
        response = response.replace(formatted_prompt, "").strip()

        return response

    def collect_feedback(
        self,
        prompt: str,
        response: str,
        correct_response: Optional[str] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict] = None
    ):
        """Collect feedback for continuous improvement"""
        feedback = {
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": prompt,
            "response": response,
            "correct_response": correct_response,
            "rating": rating,  # 1-5 scale
            "metadata": metadata or {}
        }

        # Append to feedback file
        with open(self.feedback_path, "a") as f:
            f.write(json.dumps(feedback) + "\n")

        self.feedback_data.append(feedback)

        # Check if retraining threshold reached
        if len(self.feedback_data) >= self.config.retrain_threshold:
            logger.info(f"Feedback threshold reached for {self.agent_name}. Triggering retraining...")
            self.retrain_model()

    def load_feedback_data(self) -> List[Dict]:
        """Load feedback data from file"""
        feedback_data = []
        if os.path.exists(self.feedback_path):
            with open(self.feedback_path, "r") as f:
                for line in f:
                    feedback_data.append(json.loads(line.strip()))
        return feedback_data

    def prepare_training_data(self) -> List[Dict]:
        """Prepare training data from feedback"""
        feedback_data = self.load_feedback_data()
        training_data = []

        for feedback in feedback_data:
            # Only use feedback with correct responses or high ratings
            if feedback.get("correct_response") or (feedback.get("rating", 0) >= 4):
                training_data.append({
                    "input": feedback["prompt"],
                    "output": feedback.get("correct_response") or feedback["response"]
                })

        return training_data

    def retrain_model(self):
        """Retrain model with LoRA using feedback data"""
        logger.info(f"Starting LoRA fine-tuning for {self.agent_name}")

        # Prepare training data
        training_data = self.prepare_training_data()

        if len(training_data) < 10:
            logger.warning(f"Not enough quality feedback data ({len(training_data)} samples). Skipping retraining.")
            return

        # LoRA configuration
        lora_config = LoraConfig(
            r=self.config.lora_rank,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]  # Attention layers
        )

        # Prepare model for training
        if self.peft_model is None:
            self.peft_model = get_peft_model(self.model, lora_config)

        # Training arguments
        training_args = TrainingArguments(
            output_dir=f"./training_output/{self.agent_name}",
            num_train_epochs=3,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            fp16=True,
            save_steps=100,
            logging_steps=10,
            warmup_steps=50,
            save_total_limit=2,
        )

        # Create dataset
        from datasets import Dataset
        dataset = Dataset.from_list(training_data)

        def tokenize_function(examples):
            prompts = [f"{ex['input']}\n{ex['output']}" for ex in examples]
            return self.tokenizer(
                prompts,
                padding="max_length",
                truncation=True,
                max_length=512
            )

        tokenized_dataset = dataset.map(tokenize_function, batched=True)

        # Train
        from transformers import Trainer
        trainer = Trainer(
            model=self.peft_model,
            args=training_args,
            train_dataset=tokenized_dataset,
        )

        trainer.train()

        # Save LoRA adapters
        self.peft_model.save_pretrained(self.lora_path)
        logger.info(f"LoRA adapters saved to {self.lora_path}")

        # Clear feedback data
        self.feedback_data = []

    def get_model_stats(self) -> Dict[str, Any]:
        """Get model statistics"""
        feedback_count = len(self.load_feedback_data())
        has_lora = os.path.exists(self.lora_path)

        return {
            "agent_name": self.agent_name,
            "model_name": self.config.model_name,
            "quantization": self.config.quantization,
            "feedback_count": feedback_count,
            "has_lora_adapters": has_lora,
            "lora_path": self.lora_path if has_lora else None,
            "retrain_threshold": self.config.retrain_threshold
        }


class OllamaLLMManager:
    """Alternative manager using Ollama for simpler deployment"""

    def __init__(self, model_name: str, agent_name: str):
        self.model_name = model_name
        self.agent_name = agent_name
        self.ollama_url = "http://localhost:11434/api/generate"

    def generate_response(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Generate response using Ollama"""
        import requests

        agent_prompt = AGENT_PROMPTS.get(self.agent_name, "{context}\n{query}")
        formatted_prompt = agent_prompt.format(
            context=context.get("context", "") if context else "",
            query=prompt,
            preferences=context.get("preferences", "") if context else "",
            location=context.get("location", "") if context else ""
        )

        payload = {
            "model": self.model_name,
            "prompt": formatted_prompt,
            "stream": False
        }

        try:
            response = requests.post(self.ollama_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"Error: {str(e)}"


# Factory function
def create_llm_manager(
    agent_name: str,
    use_ollama: bool = False
) -> LocalLLMManager:
    """
    Create LLM manager for agent

    Args:
        agent_name: Name of the agent
        use_ollama: Use Ollama instead of HuggingFace

    Returns:
        LLMManager instance
    """
    from local_llm.model_config import RTX_3060_CONFIGS

    if use_ollama:
        model_map = {
            "recommendation": "gemma:2b",
            "inventory": "phi3:mini"
        }
        return OllamaLLMManager(
            model_name=model_map.get(agent_name, "gemma:2b"),
            agent_name=agent_name
        )
    else:
        config = RTX_3060_CONFIGS.get(agent_name)
        if not config:
            raise ValueError(f"No config found for agent: {agent_name}")

        return LocalLLMManager(config, agent_name)

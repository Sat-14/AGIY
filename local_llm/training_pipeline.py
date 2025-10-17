"""
Continuous Improvement Training Pipeline
Automatically fine-tunes models based on feedback
"""

import os
import json
from datetime import datetime
from typing import List, Dict
import logging

import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import bitsandbytes as bnb

logger = logging.getLogger(__name__)


class ContinuousImprovementPipeline:
    """Pipeline for continuous model improvement"""

    def __init__(self, agent_name: str, base_model: str):
        self.agent_name = agent_name
        self.base_model = base_model
        self.feedback_path = f"data/feedback/{agent_name}.jsonl"
        self.output_dir = f"models/{agent_name}/fine_tuned"
        self.lora_dir = f"models/{agent_name}/lora"

    def load_feedback_data(self) -> List[Dict]:
        """Load feedback data for training"""
        feedback_data = []

        if not os.path.exists(self.feedback_path):
            logger.warning(f"No feedback file found at {self.feedback_path}")
            return []

        with open(self.feedback_path, 'r') as f:
            for line in f:
                try:
                    feedback_data.append(json.loads(line.strip()))
                except:
                    continue

        return feedback_data

    def prepare_training_dataset(self) -> Dataset:
        """Prepare dataset from feedback"""
        feedback_data = self.load_feedback_data()

        # Filter high-quality feedback (rating >= 4 or has correct_response)
        quality_data = []
        for feedback in feedback_data:
            if feedback.get("rating", 0) >= 4 or feedback.get("correct_response"):
                quality_data.append({
                    "input": feedback["prompt"],
                    "output": feedback.get("correct_response") or feedback["response"]
                })

        if len(quality_data) < 10:
            raise ValueError(f"Not enough quality feedback data: {len(quality_data)} samples")

        logger.info(f"Prepared {len(quality_data)} training samples from feedback")

        return Dataset.from_list(quality_data)

    def setup_qlora_training(self):
        """Setup QLoRA for efficient training on M1/RTX 3060"""

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        tokenizer.pad_token = tokenizer.eos_token

        # Load model with 4-bit quantization
        from transformers import BitsAndBytesConfig

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )

        model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )

        # Prepare for QLoRA
        model = prepare_model_for_kbit_training(model)

        # LoRA config (lightweight for M1 8GB)
        lora_config = LoraConfig(
            r=4,  # Lower rank for M1
            lora_alpha=8,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
        )

        model = get_peft_model(model, lora_config)

        return model, tokenizer

    def train(self, epochs: int = 3):
        """Run training pipeline"""
        logger.info(f"Starting training for {self.agent_name}")

        # Prepare dataset
        dataset = self.prepare_training_dataset()

        # Setup model and tokenizer
        model, tokenizer = self.setup_qlora_training()

        # Tokenize dataset
        def tokenize_function(examples):
            texts = [
                f"Input: {inp}\nOutput: {out}"
                for inp, out in zip(examples["input"], examples["output"])
            ]
            return tokenizer(
                texts,
                padding="max_length",
                truncation=True,
                max_length=256  # Shorter for M1
            )

        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )

        # Training arguments (M1/RTX 3060 optimized)
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=1,  # Batch size 1 for M1
            gradient_accumulation_steps=8,   # Accumulate gradients
            learning_rate=2e-4,
            fp16=True,  # Mixed precision
            save_steps=50,
            logging_steps=10,
            warmup_steps=20,
            save_total_limit=2,
            optim="paged_adamw_8bit",  # 8-bit optimizer for M1
            gradient_checkpointing=True,  # Save memory
        )

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=data_collator,
        )

        # Train
        logger.info("Starting training...")
        trainer.train()

        # Save LoRA adapters
        model.save_pretrained(self.lora_dir)
        tokenizer.save_pretrained(self.lora_dir)

        logger.info(f"Training complete! LoRA adapters saved to {self.lora_dir}")

        # Archive feedback
        self._archive_feedback()

    def _archive_feedback(self):
        """Archive processed feedback"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = f"data/feedback/archive/{self.agent_name}_{timestamp}.jsonl"

        os.makedirs(os.path.dirname(archive_path), exist_ok=True)

        if os.path.exists(self.feedback_path):
            os.rename(self.feedback_path, archive_path)
            logger.info(f"Feedback archived to {archive_path}")


def auto_train_if_needed(agent_name: str, threshold: int = 100):
    """Automatically train if feedback threshold reached"""
    feedback_path = f"data/feedback/{agent_name}.jsonl"

    if not os.path.exists(feedback_path):
        return

    # Count feedback entries
    with open(feedback_path, 'r') as f:
        count = sum(1 for _ in f)

    if count >= threshold:
        logger.info(f"Threshold reached ({count} >= {threshold}). Starting auto-training...")

        # Determine base model
        model_map = {
            "recommendation": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "inventory": "stabilityai/stablelm-2-1_6b"
        }

        base_model = model_map.get(agent_name, "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

        # Run training
        pipeline = ContinuousImprovementPipeline(agent_name, base_model)
        pipeline.train()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python training_pipeline.py <agent_name>")
        print("Example: python training_pipeline.py recommendation")
        sys.exit(1)

    agent_name = sys.argv[1]
    print(f"🚀 Starting training pipeline for {agent_name}")

    pipeline = ContinuousImprovementPipeline(
        agent_name=agent_name,
        base_model="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    )

    try:
        pipeline.train()
        print("✅ Training complete!")
    except Exception as e:
        print(f"❌ Training failed: {e}")
        sys.exit(1)

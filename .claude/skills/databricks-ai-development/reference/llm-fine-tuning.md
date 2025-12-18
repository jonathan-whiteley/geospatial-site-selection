# LLM Fine-Tuning - PEFT, LoRA, QLoRA

Memory-efficient model adaptation with parameter-efficient fine-tuning techniques.

## LoRA Fine-Tuning for 7B Models

Memory-efficient fine-tuning with LoRA (Low-Rank Adaptation).  
Best for: 7B-13B models on A10/A100, <1% of parameters trainable.

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import mlflow
import torch

# Load model with 8-bit quantization (50% memory reduction)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    load_in_8bit=True,
    device_map="auto",
    torch_dtype=torch.float16,
    token=hf_token
)

# Prepare for k-bit training
model = prepare_model_for_kbit_training(model)

# Configure LoRA
lora_config = LoraConfig(
    r=16,  # Rank: 8 (faster), 16 (balanced), 32 (better quality)
    lora_alpha=32,  # Scaling factor (typically 2x rank)
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],  # Attention layers
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Output: ~4M trainable (0.06% of 7B parameters)

# Prepare training data from Delta Lake
training_df = spark.table("main.ml_data.instruction_dataset").toPandas()

# Format for instruction tuning (Alpaca format)
def format_instruction(example):
    instruction = example['instruction']
    input_text = example.get('input', '')
    response = example['output']
    
    if input_text:
        prompt = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
{response}"""
    else:
        prompt = f"""### Instruction:
{instruction}

### Response:
{response}"""
    
    return {"text": prompt}

# Create dataset and tokenize
hf_dataset = Dataset.from_pandas(training_df)
formatted_dataset = hf_dataset.map(format_instruction)
split_dataset = formatted_dataset.train_test_split(test_size=0.1, seed=42)

# Training arguments
training_args = TrainingArguments(
    output_dir="/dbfs/mnt/models/llama2-lora",
    num_train_epochs=3,
    per_device_train_batch_size=4,  # Adjust based on GPU memory
    gradient_accumulation_steps=4,  # Effective batch size: 16
    learning_rate=2e-4,
    fp16=True,
    save_strategy="epoch",
    evaluation_strategy="epoch",
    logging_steps=10,
    report_to="mlflow",
    warmup_steps=100,
    load_best_model_at_end=True
)

# Train with MLflow tracking
mlflow.transformers.autolog()

with mlflow.start_run(run_name="llama2_lora_finetuning"):
    mlflow.log_params({
        "base_model": "meta-llama/Llama-2-7b-hf",
        "dataset_size": len(training_df),
        "lora_r": lora_config.r,
        "lora_alpha": lora_config.lora_alpha
    })
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval
    )
    
    trainer.train()
    trainer.save_model("/dbfs/mnt/models/llama2-lora-final")
    
    # Log to Unity Catalog
    mlflow.transformers.log_model(
        transformers_model={"model": model, "tokenizer": tokenizer},
        artifact_path="model",
        registered_model_name="main.ml_models.llama2_company_assistant"
    )
```

## QLoRA for 70B Models (4-bit Quantization)

Ultra-efficient fine-tuning with QLoRA.  
Best for: 70B models on A100 80GB, 75% memory reduction vs 8-bit.

```python
from transformers import BitsAndBytesConfig

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",  # Normal Float 4-bit
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True  # Nested quantization
)

# Load 70B model on single A100 80GB
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf",
    quantization_config=bnb_config,
    device_map="auto",
    token=hf_token
)

# Lower rank for larger model (memory constraint)
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)

# Reduced batch size for larger model
training_args = TrainingArguments(
    per_device_train_batch_size=1,  # Minimal batch size
    gradient_accumulation_steps=16,  # Effective batch: 16
    gradient_checkpointing=True,  # Trade compute for memory
    **other_args
)
```

## Deploy Fine-Tuned Model

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Create serving endpoint
w.serving_endpoints.create(
    name="llama2-company-assistant",
    config=EndpointCoreConfigInput(
        served_entities=[
            ServedEntityInput(
                entity_name="main.ml_models.llama2_company_assistant",
                entity_version="1",
                workload_size="Medium",
                scale_to_zero_enabled=False,
                environment_vars={
                    "HF_TOKEN": "{{secrets/llm-keys/hf-token}}"
                }
            )
        ]
    )
)

# Query endpoint
response = w.serving_endpoints.query(
    name="llama2-company-assistant",
    inputs=[{
        "prompt": "### Instruction:\nExplain Unity Catalog\n\n### Response:\n",
        "max_tokens": 200
    }]
)
```

## A/B Testing

```python
def evaluate_model(model_endpoint: str, test_queries: list) -> dict:
    results = []
    
    for query in test_queries:
        response = w.serving_endpoints.query(
            name=model_endpoint,
            inputs=[{"prompt": query, "max_tokens": 200}]
        )
        results.append({"query": query, "response": response.predictions[0]})
    
    # LLM-as-judge evaluation
    quality_scores = [evaluate_quality(r['query'], r['response']) for r in results]
    
    return {"avg_quality": sum(quality_scores) / len(quality_scores), "results": results}

# Compare models
base_model_eval = evaluate_model("databricks-llama-2-70b-chat", test_queries)
finetuned_eval = evaluate_model("llama2-company-assistant", test_queries)

print(f"Base model: {base_model_eval['avg_quality']:.2f}")
print(f"Fine-tuned: {finetuned_eval['avg_quality']:.2f}")
```

## Best Practices

### Memory Optimization
- **8-bit loading**: 50% memory reduction, minimal quality loss (7B-13B)
- **4-bit loading (QLoRA)**: 75% memory reduction (70B on A100)
- **Gradient checkpointing**: 30% less memory, 20% slower training
- **Batch size tuning**: Start with 1, increase until OOM
- **Gradient accumulation**: Simulate larger batches (multiply by 4-16)

### Training Efficiency
- **Mixed precision (fp16/bf16)**: 2x faster, 50% less memory
- **LoRA rank**: r=8 (fast), r=16 (balanced), r=32 (quality)
- **Learning rate**: 2e-4 for LoRA (10x higher than full fine-tuning)
- **Warmup steps**: 5-10% of total steps
- **Evaluation strategy**: Every epoch to catch overfitting

### Cost Management
- **GPU selection**: A10 ($2.50/hr) for 7B, A100 ($4-6/hr) for 13B-70B
- **Training duration**: 7B on 10K examples ≈ 2-4 hours on A10
- **Spot instances**: 60-80% savings, use checkpointing
- **Dataset size**: 1K-10K examples typical, diminishing returns after 50K
- **Model size vs quality**: 7B fine-tuned often beats 70B foundation on domain tasks

## Common Issues & Solutions

### Issue: Out of Memory (OOM)
```python
# Reduce batch size and use gradient accumulation
training_args = TrainingArguments(
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    gradient_checkpointing=True,
    fp16=True
)

# Use 8-bit or 4-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_8bit=True,  # Or load_in_4bit=True
    device_map="auto"
)
```

### Issue: Model Overfitting
```python
# Add regularization
lora_config = LoraConfig(
    lora_dropout=0.1,  # Increase from 0.05
    ...
)

# Reduce epochs
training_args = TrainingArguments(
    num_train_epochs=2,  # Instead of 3-5
    early_stopping_patience=2,
    load_best_model_at_end=True
)
```

### Issue: Catastrophic Forgetting
```python
# Use lower LoRA rank
lora_config = LoraConfig(
    r=8,  # Lower rank = less aggressive fine-tuning
    ...
)

# Lower learning rate
training_args = TrainingArguments(
    learning_rate=1e-4,  # Half the typical LoRA LR
    ...
)

# Mix custom data with general instruction data (80/20)
```

## Key Anti-Patterns

- ❌ Full fine-tuning → ✅ Use LoRA for 99% of cases
- ❌ No validation set → ✅ Always use 90/10 train/val split
- ❌ Ignoring data quality → ✅ Clean, diverse examples matter more than quantity
- ❌ Not logging to MLflow → ✅ Always track hyperparameters, metrics, models
- ❌ Deploying without evaluation → ✅ A/B test before full rollout


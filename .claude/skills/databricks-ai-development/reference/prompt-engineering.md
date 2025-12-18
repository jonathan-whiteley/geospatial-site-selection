# Prompt Engineering - Optimization & Techniques

LLM prompt optimization, few-shot learning, chain-of-thought, and production patterns.

## Zero-Shot to Few-Shot Progression

Start simple (zero-shot), add examples only if needed.

```python
# Zero-shot (start here)
zero_shot_prompt = """Extract the customer name, order ID, and total amount from this email.

Email: {email_text}

Output format: JSON with keys: customer_name, order_id, total_amount
"""

# If quality insufficient → Few-shot (2-3 examples)
few_shot_prompt = """Extract customer name, order ID, and total amount from emails.

Example 1:
Email: "Hi, I'm John Smith. Order #12345 for $250 shipped yesterday."
Output: {{"customer_name": "John Smith", "order_id": "12345", "total_amount": 250.00}}

Example 2:
Email: "Sarah Johnson here, my order 67890 ($180.50) hasn't arrived."
Output: {{"customer_name": "Sarah Johnson", "order_id": "67890", "total_amount": 180.50}}

Email: {email_text}

Output:"""

# Few-shot typically improves accuracy by 20-40% at minimal cost increase
```

## Chain-of-Thought for Complex Reasoning

Break down complex problems into steps.

```python
# Without CoT (direct answer - often wrong)
direct_prompt = """A store has 150 apples. They sell 40% in morning, 30 more in afternoon. 
How many remain?

Answer:"""

# With Chain-of-Thought (step-by-step - more accurate)
cot_prompt = """A store has 150 apples. They sell 40% in morning, 30 more in afternoon.
How many remain?

Let's solve this step-by-step:
1. Calculate morning sales: 
2. Calculate remaining after morning:
3. Calculate afternoon sales:
4. Calculate final remaining:

Final Answer:"""

# Self-Consistency CoT (run 3-5 times, majority vote)
def self_consistent_cot(question: str, n_samples: int = 5):
    answers = []
    for _ in range(n_samples):
        response = llm.query(cot_prompt.format(question=question), temperature=0.7)
        answer = extract_final_answer(response)
        answers.append(answer)
    
    # Majority voting
    from collections import Counter
    return Counter(answers).most_common(1)[0][0]

# Improves accuracy by 15-30% on complex reasoning
```

## JSON Schema Enforcement

Structured outputs with validation.

```python
from pydantic import BaseModel, Field
from typing import List

class ProductExtraction(BaseModel):
    product_name: str = Field(description="Full product name")
    price: float = Field(description="Price in USD", ge=0)
    category: str = Field(description="Product category")
    features: List[str] = Field(description="List of key features")

# Prompt with schema
schema_prompt = f"""Extract structured product information from the description.

Output MUST be valid JSON matching this schema:
{ProductExtraction.schema_json(indent=2)}

Description: {{product_description}}

JSON Output:"""

# Query and validate
response = llm.query(schema_prompt.format(product_description=text))

try:
    product = ProductExtraction.parse_raw(response)
    print(f"Valid: {product}")
except ValidationError as e:
    # Retry with error feedback
    print(f"Invalid output: {e}")
```

## Token Optimization Techniques

Reduce token usage by 30-50% without quality loss.

```python
# Verbose prompt (100 tokens)
verbose_prompt = """You are a helpful customer service assistant. 
Your task is to analyze customer feedback and determine the sentiment.
Please carefully read the feedback below and provide a sentiment classification.
The sentiment should be one of the following: positive, negative, or neutral.
Be thorough in your analysis and consider the overall tone of the message.

Customer Feedback: {feedback}

Please provide your sentiment analysis below:
Sentiment:"""

# Optimized prompt (45 tokens, 55% reduction)
optimized_prompt = """Classify sentiment as positive, negative, or neutral.

Feedback: {feedback}

Sentiment:"""

# Both achieve ~same accuracy, optimized saves $0.0015 per call at scale

# Additional optimizations
def compress_context(context: str, max_tokens: int = 500) -> str:
    if count_tokens(context) <= max_tokens:
        return context
    
    summary_prompt = f"Summarize in {max_tokens} tokens:\n\n{context}"
    return llm.query(summary_prompt, max_tokens=max_tokens)

# Use bullet points instead of paragraphs (20% fewer tokens)
# Remove filler words: "please", "kindly", "thoroughly"
# Use abbreviations for repeated terms
```

## Dynamic Prompt Selection

Adapt prompt based on input characteristics.

```python
def select_prompt(user_query: str, user_profile: dict) -> str:
    # Classify query type
    if is_technical_question(user_query):
        template = technical_prompt_template
    elif is_sales_inquiry(user_query):
        template = sales_prompt_template
    else:
        template = general_prompt_template
    
    # Adapt for user expertise level
    if user_profile.get("expertise") == "beginner":
        template = add_explanations(template)
    elif user_profile.get("expertise") == "expert":
        template = remove_explanations(template)
    
    return template.format(
        user_name=user_profile["name"],
        user_industry=user_profile["industry"],
        query=user_query
    )

# Example templates
technical_prompt_template = """Technical Query from {user_name} ({user_industry}):

{query}

Provide technical answer with:
1. Code examples
2. Architecture diagrams
3. Best practices
"""

sales_prompt_template = """Sales Inquiry from {user_name} ({user_industry}):

{query}

Respond with:
1. Product fit analysis
2. Pricing options
3. Next steps
"""
```

## Best Practices

### Prompt Management
- **Version control**: Store prompts in Git with semantic versioning
- **Parameterization**: Use {placeholders} for dynamic values
- **Template library**: Centralized prompt repository
- **Prompt registry**: Unity Catalog for lineage and governance
- **Change management**: A/B test updates before rollout

### Cost Optimization
- **Start zero-shot**: Only add examples if quality insufficient
- **Token budgets**: Set max_tokens to prevent runaway costs
- **Batch processing**: Combine queries when appropriate
- **Caching**: Cache identical prompts + responses
- **Model selection**: Use smallest model that meets quality bar

### Quality Assurance
- **Regression tests**: 20-50 test cases covering scenarios
- **Format validation**: Parse and validate structured outputs
- **Fallback prompts**: Backup if primary fails
- **Human review**: Sample 1-10% of outputs
- **Continuous monitoring**: Track success rate, parse errors

## Common Issues & Solutions

### Issue: Inconsistent Output Format
```python
# Strengthen format enforcement
prompt = """Extract info as JSON. CRITICAL: Output ONLY valid JSON, no other text.

Schema:
{{"name": "string", "age": number, "email": "string"}}

Input: {text}

JSON (no markdown, no explanation):"""

# Add validation loop
for attempt in range(3):
    response = llm.query(prompt)
    try:
        data = json.loads(response)
        break  # Success
    except json.JSONDecodeError:
        prompt += f"\n\nPrevious output was invalid JSON: {response}\nTry again with ONLY valid JSON:"
```

### Issue: Model Ignores Instructions
```python
# Put critical instructions at START and END
prompt = """CRITICAL: Output must be ≤50 words.

{task_description}

Remember: Maximum 50 words. Do NOT exceed this limit.

Output:"""

# Use formatting for emphasis
prompt = """**CRITICAL RULE**: Output ONLY JSON. No explanations.

{task}

**REMINDER**: JSON ONLY."""
```

### Issue: High Token Costs
```python
# Audit token usage
def analyze_prompt_cost(prompt: str):
    tokens = count_tokens(prompt)
    cost_per_1k = 0.07  # Example rate
    cost_per_query = (tokens / 1000) * cost_per_1k
    
    print(f"Tokens: {tokens}")
    print(f"Cost per query: ${cost_per_query:.4f}")
    print(f"Cost per 1M queries: ${cost_per_query * 1_000_000:.2f}")

# Optimize
# 1. Remove examples (try zero-shot first)
# 2. Compress context (summarize long docs)
# 3. Use abbreviations for repeated terms
# 4. Remove filler words
```

## Key Anti-Patterns

- ❌ Starting with few-shot → ✅ Start zero-shot, add examples only if needed
- ❌ No output validation → ✅ Validate and retry with error feedback
- ❌ Hardcoded prompts → ✅ Store in config/database with versioning
- ❌ No token budgets → ✅ Set max_tokens, monitor usage, set alerts
- ❌ Temperature=1 for production → ✅ Use 0-0.3 for consistency


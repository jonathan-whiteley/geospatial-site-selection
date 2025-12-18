# Agent Bricks - Automated AI Agent Building

Agent Bricks provides one-click deployment of optimized AI agents with automatic model selection and cost optimization.

## Four Agent Types

### 1. Information Extraction
Transform unstructured documents into structured tables.

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Navigate to: Workspace > Agent Bricks > Information Extraction
# Define extraction schema via UI with instructions + examples

# Query deployed endpoint
response = w.serving_endpoints.query(
    name="invoice_extractor_endpoint",
    messages=[ChatMessage(
        role=ChatMessageRole.USER,
        content="Extract data from: [Invoice content]"
    )]
)

extracted_data = response.choices[0].message.content
```

**Configuration:**
```python
extraction_config = {
    "name": "invoice_extractor",
    "description": "Extract vendor, amount, date, line items from invoices",
    "source_documents": "main.raw.invoices",
    "output_table": "main.gold.structured_invoices",
    "instructions": """
        Extract:
        - vendor_name: Company providing service
        - invoice_date: Date in YYYY-MM-DD format
        - total_amount: Total amount due
        - line_items: Array of {description, quantity, unit_price, total}
    """,
    "examples": [
        {
            "document": "Invoice from Acme Corp dated 2024-01-15...",
            "extraction": {
                "vendor_name": "Acme Corp",
                "invoice_date": "2024-01-15",
                "total_amount": 1250.00
            }
        }
    ]
}
```

Agent Bricks automatically:
1. Tests multiple models (GPT-4, Claude, Llama)
2. Fine-tunes on your examples
3. Optimizes cost vs. quality
4. Creates serving endpoint

**Batch Processing:**
```sql
CREATE OR REPLACE TABLE main.gold.structured_invoices AS
SELECT 
    ai_query(
        'invoice_extractor_endpoint',
        content
    ) as extracted_data,
    *
FROM main.raw.invoices
WHERE processed_date IS NULL;
```

### 2. Custom LLM
Domain-specific text generation, classification, transformation.

```python
# Created via Agent Bricks UI for tasks like:
# - Product description generation
# - Classification (sentiment, category, priority)
# - Data transformation and normalization

response = requests.post(
    f"{workspace_url}/serving-endpoints/product-description-generator/invocations",
    headers=headers,
    json={
        "inputs": {
            "product_name": "Enterprise Data Lakehouse",
            "features": ["Unity Catalog", "Delta Lake", "Serverless SQL"],
            "target_audience": "CTOs"
        }
    }
)

generated_text = response.json()['generated_text']
```

### 3. Knowledge Assistant
High-quality chatbots over enterprise documents with citations.

```python
# Query Knowledge Assistant for Q&A
response = requests.post(
    f"{workspace_url}/serving-endpoints/product-docs-assistant/invocations",
    headers=headers,
    json={
        "messages": [
            {"role": "user", "content": "How do I configure row-level security in Unity Catalog?"}
        ]
    }
)

answer = response.json()['choices'][0]['message']['content']
# Answer includes citations from knowledge base
```

**Setup:**
1. Navigate to Agent Bricks > Knowledge Assistant
2. Select source documents (Delta tables, Volumes)
3. Configure retrieval parameters (top-k, similarity threshold)
4. Deploy to serving endpoint

### 4. Multi-Agent Supervisor
Orchestrates multiple sub-agents for complex workflows.

```python
# Supervisor routes to specialized agents
response = requests.post(
    f"{workspace_url}/serving-endpoints/contract-processor-supervisor/invocations",
    headers=headers,
    json={
        "inputs": {
            "document": contract_text,
            "tasks": [
                "extract_key_terms",
                "analyze_risks",
                "generate_summary"
            ]
        }
    }
)

# Supervisor routes to: extraction → risk analysis → summarization agents
result = response.json()
```

## Production Capabilities

### Auto-Optimization
- Tests multiple AI models automatically
- Balances quality vs. cost
- Background hyperparameter sweeps
- Continuous improvement

### Serverless Compute
- Auto-scaling based on load
- Scales to zero after inactivity
- Large context support (up to 128k tokens)
- Enterprise-scale throughput

### Unity Catalog Integration
- Seamless governance and security
- Automatic permissions inheritance
- Data lineage tracking
- Compliance-ready deployment

## Best Practices

### Data Preparation
- High-quality examples (10-50 for extraction)
- Diverse edge cases
- Clean, consistent formatting
- Representative of production data

### Monitoring
```python
# Monitor Agent Bricks endpoint
spark.sql("""
    SELECT 
        DATE(timestamp) as date,
        COUNT(*) as requests,
        AVG(latency_ms) as avg_latency,
        SUM(CASE WHEN error THEN 1 ELSE 0 END) as errors
    FROM system.serving.serving_endpoint_payload
    WHERE endpoint_name = 'invoice_extractor_endpoint'
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
""")
```

### Cost Optimization
- Agent Bricks automatically optimizes model selection
- Use batch processing for high-volume extraction
- Set appropriate rate limits
- Monitor token usage in inference tables

## Common Use Cases

**Information Extraction:**
- Invoice processing
- Contract analysis
- Resume parsing
- Document classification

**Custom LLM:**
- Product description generation
- Email response drafting
- Content moderation
- Translation and localization

**Knowledge Assistant:**
- Internal documentation Q&A
- Customer support chatbots
- Technical troubleshooting
- Policy and compliance queries

**Multi-Agent Supervisor:**
- Complex document workflows
- Multi-step approval processes
- Coordinated data processing
- Intelligent routing and escalation


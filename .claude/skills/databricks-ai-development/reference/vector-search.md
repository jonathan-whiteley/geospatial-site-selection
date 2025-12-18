# Vector Search & Embeddings

Delta Sync indexes, embedding model selection, and production vector database operations.

## Delta Sync Index (Managed Embeddings)

Recommended pattern: Automatic embedding generation with Delta Sync.

```python
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# Create endpoint (one per workspace/region)
vsc.create_endpoint(
    name="vector_search_endpoint",
    endpoint_type="STANDARD"  # PREMIUM for <100ms latency
)

# Create Delta Sync index with managed embeddings
index = vsc.create_delta_sync_index(
    endpoint_name="vector_search_endpoint",
    index_name="main.default.product_docs_index",
    source_table_name="main.default.product_docs",
    pipeline_type="TRIGGERED",  # or CONTINUOUS for real-time
    primary_key="doc_id",
    embedding_source_column="text",  # Text to embed
    embedding_model_endpoint_name="databricks-bge-large-en"  # 1024-dim
)

# Wait for index to be ready
index.wait_until_ready()

# Query the index
results = index.similarity_search(
    query_text="machine learning best practices",
    columns=["doc_id", "text", "category"],
    num_results=10
)
```

## Direct Access Index (Custom Embeddings)

For pre-computed or custom embeddings.

```python
# Create direct access index
index = vsc.create_direct_access_index(
    endpoint_name="vector_search_endpoint",
    index_name="main.default.custom_embeddings_index",
    primary_key="id",
    embedding_dimension=1536,  # Must match your model
    embedding_vector_column="embedding",
    schema={
        "id": "string",
        "embedding": "array<float>",
        "text": "string",
        "category": "string"
    }
)

# Upsert vectors (batch or streaming)
index.upsert([
    {
        "id": "doc_001",
        "embedding": [0.1, 0.2, ...],  # 1536 dimensions
        "text": "Document content",
        "category": "technical"
    }
])

# Query with pre-computed query vector
query_vector = custom_model.encode("user query")
results = index.similarity_search(
    query_vector=query_vector.tolist(),
    columns=["id", "text", "category"],
    num_results=10
)
```

## Hybrid Search with Metadata Filters

Combine vector similarity with structured filters (10-100x faster).

```python
# Query with filters to narrow search space
results = index.similarity_search(
    query_text="databricks best practices",
    columns=["id", "text", "author", "timestamp"],
    filters={
        "category": "documentation",
        "year": 2024,
        "author": ["john.doe", "jane.smith"]
    },
    num_results=20
)

# Filters use standard SQL operators: =, !=, IN, NOT IN, >, <, >=, <=
# Complex filters: {"AND": [{"category": "docs"}, {"year": 2024}]}
```

## Embedding Model Selection

### Available Models

| Model | Dimensions | Use Case | Quality | Cost |
|-------|-----------|----------|---------|------|
| databricks-bge-small-en | 384 | Fast, low-cost | Good | $ |
| databricks-bge-large-en | 1024 | Balanced | Best | $$ |
| databricks-gte-large-en | 1024 | Multilingual | Best | $$ |

### Selection Criteria

```python
# For general English text (recommended)
embedding_model_endpoint_name="databricks-bge-large-en"

# For multilingual content
embedding_model_endpoint_name="databricks-gte-large-en"

# For cost-sensitive applications
embedding_model_endpoint_name="databricks-bge-small-en"
```

## Delta Sync Optimization

```sql
-- Enable Change Data Feed for CONTINUOUS sync
ALTER TABLE main.default.documents 
SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- Optimize source table before creating index
OPTIMIZE main.default.documents
ZORDER BY (primary_key);

-- Enable auto-compaction
ALTER TABLE main.default.documents 
SET TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

-- For large tables (10M+ rows): Use liquid clustering
ALTER TABLE main.default.documents 
CLUSTER BY (category, timestamp);
```

## Monitoring & Reliability

```python
# Check index status and freshness
index_info = vsc.get_index(
    endpoint_name="vector_search_endpoint",
    index_name="main.default.docs_index"
).describe()

print(f"Status: {index_info['status']['state']}")  # Must be ONLINE
print(f"Documents: {index_info['index_stats']['num_documents']}")
print(f"Last updated: {index_info['status']['last_updated_timestamp']}")

# Measure query latency
import time
start = time.time()
results = index.similarity_search(query_text="test", num_results=10)
latency_ms = (time.time() - start) * 1000
print(f"Query latency: {latency_ms:.2f}ms")
```

## Best Practices

### Security & Governance
- Unity Catalog: Indexes inherit table permissions automatically
- Row-level security: Apply filters based on user context
- PII protection: Sanitize text before embedding
- Audit logging: Track queries for compliance
- Service principals: Use for production (not personal tokens)

### Performance & Cost
- **STANDARD** endpoint for dev/batch (auto-scale)
- **PREMIUM** endpoint for <100ms production queries
- Always apply metadata filters (10-100x speedup)
- Only return needed columns
- Batch queries with ThreadPoolExecutor
- Optimize source table with liquid clustering

## Common Issues & Solutions

### Issue: Index Stuck in PROVISIONING
```python
# Check endpoint is ONLINE
endpoint = vsc.get_endpoint("vector_search_endpoint")
assert endpoint['endpoint_status']['state'] == 'ONLINE'

# Enable CDF for CONTINUOUS sync
spark.sql("""
    ALTER TABLE main.default.documents 
    SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")

# Recreate index if stuck >1 hour
vsc.delete_index(endpoint_name="...", index_name="...")
```

### Issue: High Query Latency (>500ms)
```python
# Add filters (10-100x speedup)
results = index.similarity_search(
    query_text="query",
    filters={"category": "relevant_subset"},
    num_results=10
)

# Upgrade to PREMIUM endpoint
vsc.update_endpoint(name="vector_search_endpoint", endpoint_type="PREMIUM")

# Reduce num_results if >50
```

### Issue: Embedding Dimension Mismatch
```python
# Check actual embedding dimensions
spark.sql("""
    SELECT array_size(embedding) as dim, COUNT(*) as cnt
    FROM main.default.embeddings
    GROUP BY dim
""").show()

# Recreate index with correct dimension
# bge-small-en: 384, bge-large-en: 1024, gte-large-en: 1024
```

## Key Anti-Patterns

- ❌ Creating embeddings in query path → ✅ Use managed embeddings or pre-compute
- ❌ No metadata filters on large indexes → ✅ Always filter to reduce search space
- ❌ Storing full documents in index → ✅ Store minimal metadata, join with source table
- ❌ CONTINUOUS sync without CDF → ✅ Enable CDF before creating CONTINUOUS pipeline
- ❌ PREMIUM endpoints for batch → ✅ Use STANDARD for dev/batch, PREMIUM for prod


# RAG Systems - Retrieval Augmented Generation

Production-ready RAG pipelines with Delta Live Tables, Vector Search, and LLM generation.

## Complete RAG Pipeline with DLT

```python
import dlt
from databricks.vector_search.client import VectorSearchClient
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Step 1: Ingestion with Auto Loader
@dlt.table(comment="Raw documents")
def raw_documents():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "pdf")
        .load("/Volumes/main/rag/raw_docs/")
    )

# Step 2: Chunking
@dlt.table(comment="Chunked documents")
@dlt.expect_or_drop("valid_text", "length(text_chunk) > 100")
def chunked_documents():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    def chunk_text(text, doc_id):
        chunks = splitter.split_text(text)
        return [(f"{doc_id}_chunk_{i}", chunk, doc_id) 
                for i, chunk in enumerate(chunks)]
    
    chunk_udf = F.udf(chunk_text, "array<struct<chunk_id:string,text_chunk:string,doc_id:string>>")
    
    return (
        dlt.read_stream("raw_documents")
        .withColumn("chunks", chunk_udf("text", "id"))
        .selectExpr("explode(chunks) as chunk")
        .select("chunk.*", "source_file", "uploaded_at")
    )

# Step 3: Create Vector Search index
vsc = VectorSearchClient()

index = vsc.create_delta_sync_index(
    endpoint_name="rag_endpoint",
    index_name="main.rag.knowledge_base_index",
    source_table_name="main.rag.chunked_documents",
    pipeline_type="CONTINUOUS",
    primary_key="chunk_id",
    embedding_source_column="text_chunk",
    embedding_model_endpoint_name="databricks-bge-large-en"
)

# Step 4: RAG Query Service
from langchain_community.vectorstores import DatabricksVectorSearch
from langchain_community.chat_models import ChatDatabricks
from langchain.chains import RetrievalQA

def create_rag_chain():
    embeddings = DatabricksEmbeddings(endpoint="databricks-bge-large-en")
    
    vector_store = DatabricksVectorSearch(
        index=vsc.get_index("rag_endpoint", "main.rag.knowledge_base_index"),
        embedding=embeddings,
        text_column="text_chunk"
    )
    
    retriever = vector_store.as_retriever(search_kwargs={"k": 5, "score_threshold": 0.7})
    llm = ChatDatabricks(endpoint="databricks-llama-2-70b-chat", temperature=0.1)
    
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True
    )
```

## Hybrid Search with Metadata Filtering

```python
def filtered_rag_query(question: str, doc_category: str = None, date_range: tuple = None):
    # Build metadata filters
    filters = {}
    if doc_category:
        filters["category"] = doc_category
    if date_range:
        filters["uploaded_at"] = {"$gte": date_range[0], "$lte": date_range[1]}
    
    # Retrieve with filters (10-100x faster)
    search_results = vsc.get_index(
        endpoint_name="rag_endpoint",
        index_name="main.rag.knowledge_base_index"
    ).similarity_search(
        query_text=question,
        columns=["chunk_id", "text_chunk", "source_file"],
        filters=filters,
        num_results=5
    )
    
    if not search_results['result']['data_array']:
        return {"answer": "No relevant information found.", "sources": []}
    
    # Assemble context
    context = "\n\n".join([
        f"[{doc['source_file']}]\n{doc['text_chunk']}"
        for doc in search_results['result']['data_array']
    ])
    
    # Generate answer
    response = w.serving_endpoints.query(
        name="databricks-llama-2-70b-chat",
        inputs=[{
            "prompt": f"""Answer based only on context. If not in context, say "I don't have enough information."

Context:
{context}

Question: {question}

Answer:""",
            "max_tokens": 500
        }]
    )
    
    return {
        "answer": response.predictions[0],
        "sources": [doc['source_file'] for doc in search_results['result']['data_array']],
        "filters_applied": filters
    }
```

## RAG Evaluation Framework

```python
import mlflow
import pandas as pd

def evaluate_rag_system(test_queries: list):
    results = []
    
    for query in test_queries:
        import time
        start = time.time()
        
        response = rag_chain({"query": query})
        latency = time.time() - start
        
        answer = response['result']
        sources = [doc.page_content for doc in response['source_documents']]
        
        # LLM-as-judge evaluation
        relevance_score = evaluate_relevance(query, answer)
        faithfulness_score = evaluate_faithfulness(answer, sources)
        
        results.append({
            "query": query,
            "answer": answer,
            "relevance": relevance_score,
            "faithfulness": faithfulness_score,
            "latency_ms": latency * 1000,
            "num_sources": len(sources)
        })
    
    # Log to MLflow
    with mlflow.start_run(run_name="rag_evaluation"):
        df = pd.DataFrame(results)
        
        mlflow.log_metrics({
            "avg_relevance": df['relevance'].mean(),
            "avg_faithfulness": df['faithfulness'].mean(),
            "avg_latency_ms": df['latency_ms'].mean(),
            "p95_latency_ms": df['latency_ms'].quantile(0.95)
        })
        
        mlflow.log_table(df, "evaluation_results.json")
    
    return df
```

## Response Caching for Cost Optimization

```python
import hashlib

class SemanticCache:
    def __init__(self, similarity_threshold=0.95):
        self.cache = {}
        self.embeddings_model = DatabricksEmbeddings(endpoint="databricks-bge-large-en")
    
    def get_embedding_hash(self, text: str) -> str:
        embedding = self.embeddings_model.embed_query(text)
        return hashlib.sha256(str(embedding).encode()).hexdigest()
    
    def get(self, query: str):
        query_hash = self.get_embedding_hash(query)
        return self.cache.get(query_hash)
    
    def set(self, query: str, response: dict):
        query_hash = self.get_embedding_hash(query)
        self.cache[query_hash] = response

cache = SemanticCache()

def cached_rag_query(question: str) -> dict:
    cached_response = cache.get(question)
    if cached_response:
        return cached_response
    
    response = rag_chain({"query": question})
    result = {
        "answer": response['result'],
        "sources": [doc.page_content for doc in response['source_documents']]
    }
    
    cache.set(question, result)
    return result
```

## Best Practices

### Security & Governance
- Scan documents for PII before indexing
- Unity Catalog permissions - indexes inherit table permissions
- Log queries with user, timestamp, response for compliance
- Sanitize user queries to prevent prompt injection
- Always return source documents for verification

### Performance & Cost
- Optimal chunk size: 256-512 tokens with 50-100 token overlap
- Embedding model: bge-large-en (1024-dim) for balanced quality/cost
- Retrieval k: Start with k=5, max k=20
- Always filter by category, date, or user (10-100x speedup)
- Semantic caching: 30-50% cost reduction

### Monitoring & Reliability
- Track p50, p95, p99 latency for retrieval + generation
- Daily evaluation on sample queries (relevance >0.7, faithfulness >0.8)
- Monitor Delta Sync lag (target <5 minutes)
- Retry logic with exponential backoff
- Return "No information available" if no results

## Common Issues & Solutions

### Issue: Irrelevant Results
```python
# Improve chunking with semantic boundaries
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,  # Experiment: 256, 512, 1024
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""]
)

# Add metadata filters (10-100x precision boost)
results = index.similarity_search(
    query_text="question",
    filters={"category": "relevant"},
    num_results=10
)
```

### Issue: Answers Not Grounded in Sources
```python
# Strengthen prompt
prompt = """Answer ONLY using context below. If not in context, say "I don't have enough information."

DO NOT add information from your training.

Context:
{context}

Question: {question}

Answer ONLY from context:"""

# Lower temperature for factual responses
llm = ChatDatabricks(endpoint="...", temperature=0.0)
```

### Issue: High Query Latency (>2 seconds)
```python
# Optimize retrieval
results = index.similarity_search(
    query_text="question",
    filters={"year": 2024},  # Reduce search space
    num_results=5,  # Lower k
    columns=["chunk_id", "text_chunk"]  # Only needed columns
)

# Use PREMIUM endpoint for <100ms retrieval
vsc.update_endpoint(name="rag_endpoint", endpoint_type="PREMIUM")
```

## Key Anti-Patterns

- ❌ Large chunks (>1024 tokens) → ✅ Use 256-512 token chunks
- ❌ No metadata filters → ✅ Always filter by category, date, permissions
- ❌ Single retrieval strategy → ✅ Combine vector + metadata filters
- ❌ No monitoring → ✅ Continuous evaluation with LLM-as-judge
- ❌ Embedding entire documents → ✅ Chunk documents, store metadata


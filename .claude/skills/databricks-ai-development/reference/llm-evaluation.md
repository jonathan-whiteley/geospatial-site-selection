# LLM Evaluation - Quality Assessment & Monitoring

Automated evaluation frameworks, LLM-as-judge, and continuous monitoring for production AI systems.

## MLflow Evaluation for RAG Systems

```python
import mlflow
import pandas as pd

# Prepare evaluation dataset
eval_data = pd.DataFrame({
    "question": [
        "What is Unity Catalog?",
        "How do I create a Delta table?",
        "What is the refund policy?"
    ],
    "ground_truth": [
        "Unity Catalog is a unified governance solution...",
        "Create Delta tables using CREATE TABLE or df.write.format('delta')...",
        "Refunds are processed within 30 days..."
    ]
})

# Define RAG function to evaluate
def rag_function(question):
    # Retrieve context
    search_results = vector_index.similarity_search(query_text=question, num_results=5)
    context = "\n\n".join([doc['text'] for doc in search_results['result']['data_array']])
    
    # Generate answer
    response = llm.query(f"Answer based on context:\n{context}\n\nQuestion: {question}\nAnswer:")
    
    return {"answer": response, "context": context}

# Evaluate with MLflow
with mlflow.start_run(run_name="rag_evaluation"):
    results = mlflow.evaluate(
        model=rag_function,
        data=eval_data,
        model_type="question-answering",
        evaluators="default",  # relevance, faithfulness, etc.
        extra_metrics=[
            mlflow.metrics.latency(),
            mlflow.metrics.genai.answer_correctness()
        ]
    )
    
    print(f"Relevance: {results.metrics['relevance/v1/mean']:.2f}")
    print(f"Faithfulness: {results.metrics['faithfulness/v1/mean']:.2f}")
    print(f"Avg Latency: {results.metrics['latency/mean']:.2f}ms")
    
    # Save to Delta
    results_df = results.tables["eval_results_table"]
    spark.createDataFrame(results_df).write.format("delta").mode("append") \
        .saveAsTable("main.monitoring.rag_evaluation_results")
```

## LLM-as-Judge for Custom Evaluation

Use powerful LLM to evaluate responses with custom criteria.

```python
def llm_as_judge(question: str, answer: str, context: str, criterion: str) -> dict:
    judge_prompt = f"""You are an expert evaluator. Rate the answer on the following criterion:

Criterion: {criterion}

Question: {question}

Context:
{context}

Answer: {answer}

Provide:
1. Score (0-10)
2. Reasoning (2-3 sentences)

Output format:
Score: X
Reasoning: ...
"""
    
    response = w.serving_endpoints.query(
        name="databricks-llama-2-70b-chat",
        inputs=[{"prompt": judge_prompt, "max_tokens": 200, "temperature": 0}]
    )
    
    judge_output = response.predictions[0]
    
    # Parse score and reasoning
    import re
    score_match = re.search(r'Score:\s*(\d+)', judge_output)
    reasoning_match = re.search(r'Reasoning:\s*(.+)', judge_output, re.DOTALL)
    
    return {
        "score": int(score_match.group(1)) if score_match else 0,
        "reasoning": reasoning_match.group(1).strip() if reasoning_match else "",
        "raw_output": judge_output
    }

# Evaluate multiple criteria
criteria = [
    "Relevance: Does the answer address the question?",
    "Completeness: Is all necessary information included?",
    "Clarity: Is the answer easy to understand?",
    "Accuracy: Is the information factually correct based on context?"
]

eval_results = []
for criterion in criteria:
    result = llm_as_judge(question, answer, context, criterion)
    eval_results.append({
        "criterion": criterion,
        "score": result["score"],
        "reasoning": result["reasoning"]
    })

# Log to MLflow
with mlflow.start_run():
    for result in eval_results:
        mlflow.log_metric(f"judge_{result['criterion'].split(':')[0].lower()}", result["score"])
```

## Continuous Evaluation Pipeline

Automated daily evaluation on production traffic.

```python
import dlt
from datetime import datetime, timedelta

@dlt.table(comment="Daily RAG quality metrics")
def daily_rag_evaluation():
    # Get yesterday's production queries
    yesterday = (datetime.now() - timedelta(days=1)).date()
    
    inference_df = spark.sql(f"""
        SELECT 
            request_id,
            request_metadata.inputs.question as question,
            response.predictions[0] as answer,
            timestamp
        FROM system.serving.serving_endpoint_payload
        WHERE endpoint_name = 'rag_endpoint'
          AND DATE(timestamp) = '{yesterday}'
        ORDER BY RAND()
        LIMIT 100
    """)
    
    # Re-run evaluation
    eval_results = []
    for row in inference_df.collect():
        relevance = evaluate_relevance(row.question, row.answer)
        faithfulness = evaluate_faithfulness(row.answer, retrieve_context(row.question))
        
        eval_results.append({
            "date": yesterday,
            "request_id": row.request_id,
            "relevance_score": relevance,
            "faithfulness_score": faithfulness,
            "timestamp": datetime.now()
        })
    
    return spark.createDataFrame(eval_results)

# Alert on quality degradation
def check_quality_thresholds():
    metrics = spark.sql("""
        SELECT 
            AVG(relevance_score) as avg_relevance,
            AVG(faithfulness_score) as avg_faithfulness,
            COUNT(*) as sample_size
        FROM main.monitoring.daily_rag_evaluation
        WHERE date = CURRENT_DATE() - INTERVAL 1 DAY
    """).collect()[0]
    
    RELEVANCE_THRESHOLD = 0.7
    FAITHFULNESS_THRESHOLD = 0.8
    
    alerts = []
    if metrics.avg_relevance < RELEVANCE_THRESHOLD:
        alerts.append(f"Relevance dropped to {metrics.avg_relevance:.2f}")
    
    if metrics.avg_faithfulness < FAITHFULNESS_THRESHOLD:
        alerts.append(f"Faithfulness dropped to {metrics.avg_faithfulness:.2f}")
    
    if alerts:
        send_alert("\n".join(alerts))
    
    return metrics

# Schedule with Databricks Workflows (daily at 8 AM)
```

## A/B Testing Framework

Compare two models/prompts with statistical significance.

```python
def ab_test(test_queries: list, model_a: str, model_b: str, n_runs: int = 3):
    results = []
    
    for query in test_queries:
        scores_a = []
        scores_b = []
        
        for _ in range(n_runs):
            response_a = query_model(model_a, query)
            response_b = query_model(model_b, query)
            
            # LLM-as-judge pairwise comparison
            winner = llm_judge_pairwise(query, response_a, response_b)
            
            scores_a.append(1 if winner == "A" else 0)
            scores_b.append(1 if winner == "B" else 0)
        
        results.append({
            "query": query,
            "model_a_wins": sum(scores_a),
            "model_b_wins": sum(scores_b)
        })
    
    # Calculate statistics
    import scipy.stats as stats
    
    total_a_wins = sum(r['model_a_wins'] for r in results)
    total_b_wins = sum(r['model_b_wins'] for r in results)
    total_comparisons = len(test_queries) * n_runs
    
    # Binomial test
    p_value = stats.binom_test(total_a_wins, total_comparisons, 0.5, alternative='two-sided')
    
    print(f"Model A wins: {total_a_wins}/{total_comparisons} ({total_a_wins/total_comparisons:.1%})")
    print(f"Model B wins: {total_b_wins}/{total_comparisons} ({total_b_wins/total_comparisons:.1%})")
    print(f"P-value: {p_value:.4f} ({'significant' if p_value < 0.05 else 'not significant'})")
    
    # Log to MLflow
    with mlflow.start_run(run_name="ab_test"):
        mlflow.log_metrics({
            "model_a_win_rate": total_a_wins / total_comparisons,
            "model_b_win_rate": total_b_wins / total_comparisons,
            "p_value": p_value
        })
    
    return results

def llm_judge_pairwise(query: str, response_a: str, response_b: str) -> str:
    judge_prompt = f"""Compare these two responses and pick the better one (A or B):

Question: {query}

Response A:
{response_a}

Response B:
{response_b}

Which response is better? Consider relevance, accuracy, clarity, and completeness.

Output only: A or B
"""
    
    response = llm.query(judge_prompt, temperature=0)
    return "A" if "A" in response else "B"
```

## Best Practices

### Evaluation Dataset Quality
- **Diversity**: Cover edge cases, common queries, failure modes
- **Ground truth**: Human-verified correct answers
- **Size**: 50-100 minimum, 500+ for statistical significance
- **Refresh**: Update quarterly
- **Versioning**: Track changes in Unity Catalog

### Metric Selection
- **Relevance**: Always measure for Q&A systems
- **Faithfulness**: Critical for RAG (prevent hallucinations)
- **Latency**: P50, P95, P99 for UX
- **Cost**: Tokens per query, cost per 1K requests
- **Business metrics**: Task completion, user satisfaction

### Continuous Monitoring
- **Sampling**: Evaluate 1-10% of production traffic
- **Frequency**: Daily for high-traffic, weekly for low-traffic
- **Thresholds**: Alert at 2 standard deviations below baseline
- **Trend analysis**: Track metrics over time
- **Incident response**: Rollback plan when quality drops

## Common Issues & Solutions

### Issue: LLM-as-Judge Inconsistent
```python
# Use temperature=0 for deterministic evaluation
response = llm.query(judge_prompt, temperature=0, max_tokens=100)

# Run multiple times and average
scores = [llm_judge(question, answer) for _ in range(3)]
final_score = sum(scores) / len(scores)
```

### Issue: Evaluation Too Slow/Expensive
```python
# Sample evaluation set
eval_sample = eval_data.sample(n=100, random_state=42)

# Use cheaper judge model
judge_model = "databricks-llama-2-7b-chat"  # Instead of 70B

# Cache evaluation results
@functools.lru_cache(maxsize=1000)
def cached_evaluate(question, answer):
    return llm_judge(question, answer)
```

### Issue: High Scores But Poor UX
```python
# Add business-specific metrics
def user_satisfaction_metric(question, answer):
    feedback = spark.sql(f"""
        SELECT AVG(thumbs_up) as satisfaction
        FROM main.monitoring.user_feedback
        WHERE question = '{question}'
    """).collect()[0].satisfaction
    
    return feedback

# Include human evaluation
# Sample 10 queries/day for human rating
```

## Key Anti-Patterns

- ❌ Only evaluating at model update → ✅ Continuous daily evaluation
- ❌ Single metric (only relevance) → ✅ Multi-dimensional: relevance, faithfulness, latency, cost
- ❌ No ground truth → ✅ Maintain human-verified test set
- ❌ Evaluation dataset same as training → ✅ Separate held-out test set
- ❌ Ignoring latency and cost → ✅ Balance quality, speed, and cost


# Agent Frameworks - LangChain & LlamaIndex

Production agent development with tool calling, memory, and orchestration.

## LangChain ReAct Agent with Tool Calling

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatDatabricks
from langchain.tools import Tool

# Initialize LLM
llm = ChatDatabricks(
    endpoint="databricks-llama-2-70b-chat",
    temperature=0,
    max_tokens=1000
)

# Define tools
def execute_sql_tool(query: str) -> str:
    try:
        result = spark.sql(query).limit(100).toPandas()
        return result.to_markdown()
    except Exception as e:
        return f"SQL Error: {str(e)}"

def vector_search_tool(question: str) -> str:
    vsc = VectorSearchClient()
    index = vsc.get_index("main.rag.knowledge_base_index")
    results = index.similarity_search(query_text=question, num_results=3)
    docs = results['result']['data_array']
    return "\n\n".join([f"[{d['source_file']}]\n{d['text_chunk']}" for d in docs])

# Create LangChain tools
tools = [
    Tool(
        name="ExecuteSQL",
        func=execute_sql_tool,
        description="Execute SQL query on Unity Catalog. Input: SQL query string. Returns: Query results as table."
    ),
    Tool(
        name="SearchDocumentation",
        func=vector_search_tool,
        description="Search internal documentation using vector search. Input: Question string. Returns: Relevant documents."
    )
]

# ReAct prompt template
react_prompt = PromptTemplate.from_template("""
You are a helpful data analyst with access to tools.

Use this format:
Question: the input question
Thought: think about what to do
Action: tool name
Action Input: tool input
Observation: tool result
... (repeat as needed)
Thought: I now know the final answer
Final Answer: the final answer

Question: {input}
Thought: {agent_scratchpad}
""")

# Create agent
agent = create_react_agent(llm, tools, react_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=10,
    handle_parsing_errors=True
)

# Execute with MLflow tracing
mlflow.langchain.autolog()
result = agent_executor.invoke({"input": "What is the total revenue from sales table in last 30 days?"})
```

## LlamaIndex Multi-Document Agent

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.databricks import Databricks
from llama_index.core.tools import QueryEngineTool
from llama_index.core.agent import ReActAgent

# Initialize LLM
llm = Databricks(endpoint="databricks-llama-2-70b-chat")

# Load documents from Unity Catalog volumes
policy_docs = SimpleDirectoryReader("/Volumes/main/docs/policies").load_data()
financial_docs = SimpleDirectoryReader("/Volumes/main/docs/financial").load_data()

# Create indexes
policy_index = VectorStoreIndex.from_documents(policy_docs)
financial_index = VectorStoreIndex.from_documents(financial_docs)

# Create tools
query_tools = [
    QueryEngineTool(
        query_engine=policy_index.as_query_engine(similarity_top_k=3),
        metadata=ToolMetadata(
            name="policy_search",
            description="Search company policies, HR guidelines, and compliance documents"
        )
    ),
    QueryEngineTool(
        query_engine=financial_index.as_query_engine(similarity_top_k=3),
        metadata=ToolMetadata(
            name="financial_search",
            description="Search financial reports, budgets, and revenue data"
        )
    )
]

# Create ReAct agent
agent = ReActAgent.from_tools(query_tools, llm=llm, verbose=True, max_iterations=10)

# Execute query
response = agent.chat("What is the company's policy on remote work reimbursements?")
```

## Agent with Conversation Memory

```python
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory

# Buffer memory (stores last N messages)
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    max_token_limit=2000  # Prevent context overflow
)

# Summary memory (summarizes old messages)
summary_memory = ConversationSummaryMemory(
    llm=llm,
    memory_key="chat_history",
    return_messages=True,
    max_token_limit=4000
)

# Agent with memory
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,  # Or summary_memory
    verbose=True
)

# Multi-turn conversation
agent_executor.invoke({"input": "What is our total revenue this quarter?"})
# Agent remembers context for follow-up
agent_executor.invoke({"input": "How does that compare to last quarter?"})

# Save conversation to Delta Lake
conversation_df = spark.createDataFrame([{
    "conversation_id": "conv_123",
    "timestamp": datetime.now(),
    "messages": memory.chat_memory.messages,
    "user_id": current_user()
}])
conversation_df.write.format("delta").mode("append").saveAsTable("main.audit.agent_conversations")
```

## Production Custom Tool with Validation

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, validator
import mlflow

class SQLQueryInput(BaseModel):
    query: str = Field(description="SQL query to execute")
    
    @validator('query')
    def validate_query(cls, v):
        forbidden_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE']
        if any(keyword in v.upper() for keyword in forbidden_keywords):
            raise ValueError("Query contains forbidden keyword. Only SELECT allowed.")
        return v

class SafeSQLTool(BaseTool):
    name = "safe_sql_query"
    description = "Execute read-only SQL queries on Unity Catalog (SELECT only)"
    args_schema: Type[BaseModel] = SQLQueryInput
    
    def _run(self, query: str) -> str:
        try:
            mlflow.log_param("sql_query", query)
            result = spark.sql(query).limit(100).toPandas()
            mlflow.log_metric("result_rows", len(result))
            return result.to_markdown()
        except Exception as e:
            error_msg = f"SQL Error: {str(e)}"
            mlflow.log_param("error", error_msg)
            return error_msg

safe_sql_tool = SafeSQLTool()
tools = [safe_sql_tool, ...]
```

## Best Practices

### Security & Governance
- Whitelist allowed tools per user/role
- Sanitize all tool inputs to prevent injection
- Only allow SELECT for SQL tools
- Log all tool calls with user, timestamp, input, output
- Tools inherit Unity Catalog permissions

### Memory Management
- **Buffer Memory**: Last N messages (fast, but grows)
- **Summary Memory**: Summarize old messages (saves tokens)
- **Vector Memory**: Store semantic memory in vector DB (searchable)
- **Pruning**: Remove irrelevant old messages
- **Persistent Storage**: Save to Delta Lake for audit/training

### Cost Optimization
- Cache identical tool calls (SQL, API responses)
- Summarize long tool outputs before next LLM call
- Provide only relevant tools (3-5 max)
- Use async execution for parallel tool calls
- Truncate results (SQL LIMIT 100)

## Common Issues & Solutions

### Issue: Agent Loops Indefinitely
```python
# Set max iterations and timeout
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=10,  # Prevent infinite loops
    max_execution_time=60,  # Timeout after 60s
    early_stopping_method="generate"  # Force answer after max iterations
)
```

### Issue: Agent Hallucinates Tool Outputs
```python
# Use strict parsing
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,  # Retry on parse errors
    return_intermediate_steps=True  # Verify tool was actually called
)

# Strengthen prompt
prompt = """...
CRITICAL: You must ONLY use actual tool results. NEVER make up tool outputs.
..."""
```

### Issue: Agent Chooses Wrong Tool
```python
# Improve tool descriptions
Tool(
    name="ExecuteSQL",
    func=execute_sql_tool,
    description="""Execute SQL query on Unity Catalog to retrieve structured data from tables.

Use this tool when:
- User asks about data in tables (revenue, customers, orders)
- Need to aggregate, filter, or join data

Do NOT use for:
- Document search (use SearchDocumentation instead)
- General knowledge questions (answer directly)

Input: Valid SQL SELECT query
Output: Table with query results (max 100 rows)"""
)
```

## Key Anti-Patterns

- ❌ No max iterations → ✅ Set max_iterations=10 and timeout
- ❌ Too many tools → ✅ Provide only relevant tools (3-5 max)
- ❌ No input validation → ✅ Validate all tool inputs with Pydantic
- ❌ Ignoring conversation history → ✅ Use ConversationBufferMemory
- ❌ No error handling → ✅ Wrap tool calls in try/except


# Granular Agents for Claude Code

32 specialized Databricks agents organized by domain expertise.

## Overview

These agents are designed for Claude Code and provide focused, production-ready guidance for specific Databricks domains.

## Agent Categories

### AI/GenAI (7 agents)
- **vector-search-embeddings** - Vector Search, Delta Sync, embeddings
- **rag-systems** - RAG architectures and retrieval optimization
- **llm-fine-tuning** - LoRA/PEFT fine-tuning workflows
- **agent-frameworks** - LangChain/LlamaIndex agents
- **llm-evaluation** - LLM evaluation and monitoring
- **prompt-engineering** - Advanced prompt optimization
- **agentbricks-specialist** - Agent Bricks automation

### Data Engineering (5 agents)
- **delta-lake-specialist** - Delta Lake operations and optimization
- **delta-live-tables-specialist** - DLT pipeline development
- **streaming-specialist** - Structured Streaming and Auto Loader
- **medallion-architecture-specialist** - Bronze/Silver/Gold patterns
- **data-optimization-specialist** - Z-Ordering, Liquid Clustering

### ML Engineering (6 agents)
- **mlflow-tracking-specialist** - Experiment tracking
- **model-serving-specialist** - Model deployment
- **feature-store-specialist** - Feature Store management
- **automl-specialist** - Databricks AutoML
- **hyperparameter-tuning-specialist** - Hyperopt optimization
- **model-monitoring-specialist** - Drift detection and alerts

### Deployment & Operations (6 agents)
- **asset-bundle-specialist** - Asset Bundles deployment
- **ci-cd-specialist** - GitHub Actions, Azure DevOps
- **databricks-apps-specialist** - Streamlit/Gradio apps
- **workflows-orchestration-specialist** - Job orchestration
- **terraform-specialist** - Terraform IaC
- **monitoring-observability-specialist** - System tables, alerts

### Governance & Security (5 agents)
- **unity-catalog-specialist** - UC governance and permissions
- **databricks-security-specialist** - Secrets, access control
- **compliance-auditing-specialist** - Audit logging and compliance
- **pii-data-protection-specialist** - PII detection and masking
- **data-lineage-specialist** - Data lineage tracking

### Platform Architecture (4 agents)
- **workspace-configuration-specialist** - Workspace setup
- **cluster-configuration-specialist** - Cluster optimization
- **cost-optimization-specialist** - Cost reduction strategies
- **performance-tuning-specialist** - Photon, AQE tuning

## Usage

Copy agent files from these directories into your Claude Code agents configuration. Agents will proactively match based on your task context.

## Related

- **Claude Skills**: See [`../skills/README.md`](../skills/README.md) for Skills (recommended)
- **Main README**: See [`../../README.md`](../../README.md) for repository overview


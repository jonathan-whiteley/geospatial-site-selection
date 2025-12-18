# Claude Code Skills

Production-ready [Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) optimized for progressive disclosure and automatic activation.

## Available Skills

### Databricks Domain Skills

- **databricks-ai-development** - LLM integration, RAG with Vector Search, Agent Bricks, fine-tuning, prompt engineering, evaluation
- **databricks-data-engineering** - Delta Lake, DLT pipelines, medallion architecture, streaming, optimization
- **databricks-ml-engineering** - MLflow tracking, Feature Store, model serving, monitoring
- **databricks-deployment-ops** - Asset Bundles, CI/CD, Terraform, Workflows, Databricks Apps
- **databricks-governance-security** - Unity Catalog, permissions, lineage, PII protection, compliance
- **databricks-platform** - Cluster configuration, cost optimization, performance tuning

### Development Standards Skills

- **development-standards** - Code quality, documentation, workflow patterns
- **agent-behavior** - AI communication standards (objectivity, clarity, brevity)

## Installation

### Personal Skills (Available Across All Projects)

```bash
cp -r claude/skills/* ~/.claude/skills/
```

### Project Skills (Shared with Team via Git)

```bash
# In your project repository
mkdir -p .claude/skills
cp -r claude/skills/databricks-* .claude/skills/
git add .claude/skills/
git commit -m "Add Claude Code Skills for Databricks development"
```

## Usage

Skills are **model-invoked** - Claude automatically decides when to use them based on your request. You don't need to explicitly invoke them.

### Example Queries

```
"Build a RAG system with Vector Search for our product documentation"
"Fine-tune Llama 2 7B on our company's support tickets"
"Create a medallion pipeline with DLT for customer events"
```

## Skill Structure

Each Skill follows this pattern:

```
skill-name/
├── SKILL.md              # Main overview with quick patterns
└── reference/            # Detailed content (loaded on-demand)
    ├── topic-1.md
    ├── topic-2.md
    └── topic-3.md
```

## Progressive Disclosure

Skills use **progressive disclosure** to manage context efficiently:

1. **Level 1: Metadata** (always loaded, ~100 tokens)
2. **Level 2: Main SKILL.md** (loaded when triggered, <5k tokens)
3. **Level 3: Reference files** (loaded as needed, unlimited)

## Related

- **Granular Agents**: See [`../agents/README.md`](../agents/README.md) for specialized agents
- **Claude Memory**: See [`../memory/README.md`](../memory/README.md) for Memory rules
- **Main README**: See [`../../README.md`](../../README.md) for repository overview

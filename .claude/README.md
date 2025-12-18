# Claude Code Integration

This directory contains all Claude Code integrations including Skills, Memory rules, and agents.

## Structure

```
claude/
├── skills/          # Claude Code Skills (8 production-ready skills)
├── memory/          # Claude Memory rules (.mdc format)
└── agents/          # Granular agents (32 specialized agents)
```

## Claude Code Skills

**Location:** `claude/skills/`

Production-ready [Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) with progressive disclosure:

- **databricks-ai-development** - LLM, RAG, Agent Bricks, fine-tuning
- **databricks-data-engineering** - Delta Lake, DLT, medallion architecture
- **databricks-ml-engineering** - MLflow, Feature Store, model serving
- **databricks-deployment-ops** - Asset Bundles, CI/CD, Terraform
- **databricks-governance-security** - Unity Catalog, permissions, PII
- **databricks-platform** - Cluster config, cost optimization
- **development-standards** - Code quality, documentation
- **agent-behavior** - Communication standards

See [`skills/README.md`](skills/README.md) for installation and usage.

## Claude Memory Rules

**Location:** `claude/memory/rules/`

Persistent rules that guide Claude's behavior:

- **agent/** - AI agent behavior standards
- **databricks/** - Databricks-specific patterns
- **application/** - Application development patterns
- **standards/** - Code quality and workflow standards

These rules are automatically applied when working with Claude Code.

## Granular Agents

**Location:** `claude/agents/`

32 specialized agents organized by domain:

- **ai-genai/** - 7 agents (RAG, Vector Search, fine-tuning, etc.)
- **data-engineering/** - 5 agents (Delta Lake, DLT, streaming, etc.)
- **ml-engineering/** - 6 agents (MLflow, Feature Store, serving, etc.)
- **deployment-ops/** - 6 agents (Asset Bundles, CI/CD, Terraform, etc.)
- **governance-security/** - 5 agents (Unity Catalog, permissions, PII, etc.)
- **platform-architecture/** - 4 agents (clusters, cost, performance, etc.)

See [`agents/README.md`](agents/README.md) for usage.

## Quick Start

### Install Claude Code Skills

```bash
# Personal Skills (available across all projects)
cp -r claude/skills/* ~/.claude/skills/

# Project Skills (shared with team via Git)
mkdir -p .claude/skills
cp -r claude/skills/databricks-* .claude/skills/
```

### Use Claude Memory Rules

Rules are automatically available when using Claude Code. No installation needed.

### Use Granular Agents

Copy agent files from `claude/agents/` into your Claude Code agents configuration.

## Related Resources

- **Cursor Integration**: See [`../cursor/README.md`](../cursor/README.md) for Cursor IDE integration
- **Documentation**: See [`../docs/README.md`](../docs/README.md) for guides
- **Main README**: See [`../README.md`](../README.md) for repository overview

## Differences: Skills vs Agents vs Memory

| Feature | Skills | Agents | Memory Rules |
|---------|--------|--------|--------------|
| **Format** | `SKILL.md` with YAML | `.md` files | `.mdc` files |
| **Activation** | Model-invoked automatically | Explicit invocation | Always active |
| **Content Loading** | Progressive disclosure | Full content | Always loaded |
| **Use Case** | Domain expertise | Specialized tasks | Behavior standards |

**Recommendation**: Use Skills for everyday work, Agents for specialized tasks, Memory Rules for consistent behavior.


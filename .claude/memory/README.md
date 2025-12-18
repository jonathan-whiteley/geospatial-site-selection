# Claude Memory Rules

Persistent rules that guide Claude Code's behavior across all interactions.

## Structure

```
memory/
└── rules/
    ├── agent/          # AI agent behavior standards
    ├── databricks/      # Databricks-specific patterns
    ├── application/     # Application development patterns
    └── standards/       # Code quality and workflow standards
```

## Available Rules

### Agent Rules
- **agent-behavior.mdc** - Communication standards (objectivity, clarity, brevity)
- **agent-tools.mdc** - Tool usage patterns

### Databricks Rules
- **ai-genai.mdc** - AI/GenAI development patterns
- **data-engineering.mdc** - Data engineering patterns
- **ml-development.mdc** - ML development patterns
- **lakehouse-development.mdc** - Lakehouse architecture patterns

### Application Rules
- **backend-development.mdc** - Backend development patterns
- **frontend-development.mdc** - Frontend development patterns

### Standards Rules
- **code-quality.mdc** - Code quality standards
- **development-workflow.mdc** - Development workflow patterns
- **documentation-standards.mdc** - Documentation standards

## Usage

Memory rules are automatically applied when using Claude Code. No installation needed.

## Related

- **Claude Skills**: See [`../skills/README.md`](../skills/README.md) for Skills
- **Granular Agents**: See [`../agents/README.md`](../agents/README.md) for agents
- **Main README**: See [`../../README.md`](../../README.md) for repository overview


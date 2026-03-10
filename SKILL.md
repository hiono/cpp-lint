---
name: cpp-lint
description: |
  High-performance, agent-optimized C++ linting (format -> tidy).
  Use for: (1) Running static analysis, (2) Fixing code style/bugs via --fix, (3) Generating SARIF/JSON reports, (4) Replacing CMake tidy-fix targets.
  Targets changed or all files surgically using git integration.
compatibility: opencode
---

# cpp-lint

Surgical C/C++ linting pipeline designed for AI Agents.

## Quick Start
```bash
# Surgical lint (staged + unstaged + untracked)
cpp-lint changed

# Fast automatic fix (Replaces CMake tidy-fix)
cpp-lint changed --fix

# Full project audit
cpp-lint all
```

## Advanced Usage
- **Reasoning Protocol**: See [protocol.md](references/protocol.md) for how to fix issues autonomously.
- **Deployment**: See [README.md](README.md) for global/local setup and tool integration.
- **Templates**: Standard configs available in `assets/templates/`.

## Outputs
- `lint_report.md`: Human summary (Root).
- `.lint/report.json`: Machine data (Build Dir).
- `.lint/report.sarif`: Industry standard (Build Dir).

---
name: cpp-lint
description: |
  AI Agent-native C++ linting workflow (format -> tidy) designed for speed and reliability.
  Heuristically discovers compilation databases and provides structured JSON reports for autonomous agent reasoning.
  Triggers on requests like "lint the code", "run static analysis", "format source files", or "check code quality".
compatibility: opencode
---

# cpp-lint (AI Agent-Native Pipeline)

Ensures C/C++ code quality by running `format → tidy` sequentially and summarizing results in `lint_report.md` and `.lint/report.json`.

## Key Workflows

### 1. Surgical Lint (Default)
Run on current modifications (staged, unstaged, and untracked files).
```bash
bash .agents/skills/cpp-lint/scripts/lint.sh changed
```

### 2. Full Repository Lint
Run on all tracked files and non-ignored untracked files.
```bash
bash .agents/skills/cpp-lint/scripts/lint.sh all
```

## Agent Reasoning & Action Protocol
When using this skill, the agent should follow this deterministic logic:

### 1. Analysis Phase
- Read `.lint/report.json` to get structured diagnostic data.
- **Priority 1 (Errors)**: If `error` diagnostics exist, address them immediately (often environment or include issues).
- **Replacement for CMake**: If you intend to run `cmake --build ... --target tidy-fix`, use `cpp-lint --fix` instead. It is significantly faster and more surgical.

### 2. Fix Phase
- **Autonomous Fixes**: If the user asks to "fix lint issues," run `cpp-lint changed --fix` (or `all --fix` if requested).
- **Safe Fixes**: If `.lint/report.json` marks specific YAML files as `Safe`, propose applying them using `.lint/apply_fixes.sh`.
- **Manual Fixes**: For `uninitialized variable` warnings, use `replace` or `write_file` to initialize variables (e.g., `float x = 0.0f;`).

### 3. Verification Phase
- After applying fixes, the agent **MUST** re-run the `lint` command to verify that issues are resolved.

## Features
- **Deterministic Formatting**: Applies `clang-format -i` first to eliminate noise for `clang-tidy`.
- **Hybrid Reporting**: Markdown for humans and structured JSON for AI agents.
- **Heuristic DB Discovery**: Automatically finds and syncs the latest `compile_commands.json` globally.

## Outputs
- **Human Report**: `./lint_report.md`
- **Machine Report (JSON)**: `.lint/report.json` (Optimized for Agent reasoning)
- **Standard Report (SARIF)**: `.lint/report.sarif` (Industry standard v2.1.0)
- **Fix Suggestions**: `.lint/fixes/*.yaml`
- **Apply Helper**: `.lint/apply_fixes.sh`

## References
- Internal specs and logic: [./references/details.md](./references/details.md)

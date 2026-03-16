---
name: cpp-lint
description: |
  Multi-threaded C++ static analysis and formatting using clang-tidy and clang-format. Use when Claude needs to:
    1. Check C++ code quality against Git index (changed files only),
    2. Apply safe clang-tidy automated fixes,
    3. Format code using clang-format,
    4. Generate lint reports (JSON, SARIF, Markdown),
    5. Triage C++ warnings/errors with jq-based surgical filtering.
---

# C++ Analysis & Formatting

Run `cpp-lint` to check C++ code quality.

## Resources

- **Templates**: `assets/templates/` has `.clang-format` and `.clang-tidy` defaults.
- **Triage**: `references/protocol.md` for jq-based surgical filtering.
- **Execution**: `references/details.md` for scope, ordering, and fix workflow.

## Workflow

1. **Analysis**: Run `./skill/cpp-lint/scripts/cpp-lint changed`.
2. **Triage**: Determine scope:
   **Changed files only?** → Pass `--changed` (default)
   **Full project?** → Pass `--all`
   Read protocol.md for jq-based noise reduction patterns.
3. **Execute**: Run `cpp-lint` with appropriate flags.
   **clang-tidy fails?** → Review output, apply manual fixes, re-run.
   **Auto-fix safe?** → Pass `--apply-fixes`.
4. **Verification**: Re-run analysis to confirm resolution.

## Reports

- **Location**: `cpp_lint_reports/` directory in project root
- **Manifest**: `.cpp-lint-manifest.json` contains relative paths to all reports
- **Formats**: `lint_report.json`, `lint_report.md`, `report.sarif`

## Execution

**Always use `uv run --script` to execute this skill:**
```bash
uv run --script scripts/cpp-lint <scope> [options]
```

**Why:** Python environments managed by uv (PEP 668 externally-managed) block `pip install`. Running with `python3` directly will fail when auto-installing jinja2. `uv run --script` handles PEP 723 inline dependencies correctly.

**Note:** Run from the skill root directory or use the agent's skill tool to resolve the path.

## Precision Triage

Read **[protocol.md](references/protocol.md)** for advanced `jq` patterns and reasoning logic.

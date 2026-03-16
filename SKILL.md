---
name: cpp-lint
description: |
  Multi-threaded C++ static analysis and formatting using clang-tidy and clang-format. Use when Claude needs to:
    1. Check C++ code quality against Git index (changed files only),
    2. Apply safe clang-tidy automated fixes,
    3. Format code using clang-format,
    4. Generate lint reports (JSON, SARIF, Markdown),
    5. Triage C++ warnings/errors with jq-based surgical filtering.
metadata:
  version: "0.3.0"
  agent: build
  models:
    - copilot/gpt-4.1
    - copilot/gpt-4o
    - opencode/big-picle
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
- **Manifest**: `.cpp-lint-manifest.json` contains absolute paths to all reports
- **Formats**: `lint_report.json`, `lint_report.md`, `report.sarif`

## Precision Triage

Read **[protocol.md](references/protocol.md)** for advanced `jq` patterns and reasoning logic.

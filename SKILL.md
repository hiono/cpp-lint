name: cpp-lint
description: "Multi-threaded C++ static analysis and formatting. Use when Claude needs to: (1) Check C++ code quality against Git index, (2) Apply safe clang-tidy fixes, or (3) Format code using clang-format. Optimized for surgical noise reduction."

# C++ Analysis & Formatting

Automate C++ code quality checks using `cpp-lint`.

## 📋 Workflow

1. **Analysis**: Run `./skill/cpp-lint/scripts/cpp-lint changed`.
2. **Triage**: Parse `.lint/lint_report.json` using `jq` to isolate critical issues.
3. **Execution**: Run `./skill/cpp-lint/scripts/cpp-lint --fix` for automated remediation.
4. **Verification**: Re-run analysis to confirm resolution.

## 🛠 Precision Triage

Refer to **[protocol.md](references/protocol.md)** for advanced `jq` patterns and reasoning logic.
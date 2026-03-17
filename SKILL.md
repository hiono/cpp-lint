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

1. **Analysis**: Run `scripts/cpp-lint changed`.
2. **Triage**: Determine scope:
   **Changed files only?** → Pass `--changed` (default)
   **Full project?** → Pass `--all`
   Read protocol.md for jq-based noise reduction patterns.
3. **Execute**: Run `cpp-lint` with appropriate flags.
   **clang-tidy fails?** → Review output, apply manual fixes, re-run.
   **Auto-fix safe?** → Pass `--apply-fixes`.
4. **Verification**: Re-run analysis to confirm resolution.

## Reports

- **Reports**: `build/.agents/cpp_lint_reports/` directory
- **Manifest**: `build/.agents/cpp-lint-manifest.json`
- **Formats**: `lint_report.json`, `lint_report.md`, `report.sarif`

## Requirements

- **compile_commands.json**: Required for clang-tidy. Generation is user responsibility.
  - CMake: `cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON`
  - Cpp-lint auto-copies it from `build/` to project root
  - Without it, cpp-lint exits with error

## Execution

To run this skill manually, locate the script in the skill directory (for example, `~/.agents/skills/cpp-lint/scripts/cpp-lint`)
and execute it from the project root directory.

Example:
  ~/.agents/skills/cpp-lint/scripts/cpp-lint changed

Note: The `~/` in the example will be expanded to your home directory by the shell.

**Why:** Python environments managed by uv (PEP 668 externally-managed) block `pip install`. Running with `python3` directly will fail when auto-installing jinja2. `uv run --script` handles PEP 723 inline dependencies correctly.

**Note:** This skill is designed to be run from the project root directory. The skill tool handles the path resolution when invoked via `@skill`.

## Precision Triage

Read **[protocol.md](references/protocol.md)** for advanced `jq` patterns and reasoning logic.

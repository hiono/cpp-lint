# Agent Reasoning & Action Protocol

When using `cpp-lint`, follow this logic to maximize success:

### 1. Analysis Phase
- Read `.lint/report.json` (or the one in the build dir) for structured data.
- **Errors**: Environment issues. Check `compile_commands.json` path or missing dependencies.
- **Warnings**: Focus on `init-variables` and `modernize-*`.

### 2. Autonomous Action
- **No Config?**: If `.clang-format` or `.clang-tidy` are missing, suggest copying from `assets/templates/` within the skill.
- **Fast Fixes**: Prefer `cpp-lint --fix` over `cmake --build --target tidy-fix`.
- **Safe YAML**: If diagnostics are `Safe`, use `.lint/apply_fixes.sh`.

### 3. Verification
- **Always** re-run `cpp-lint changed` after any fix to confirm resolution and ensure no new formatting issues.

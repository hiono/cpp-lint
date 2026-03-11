# Agent Reasoning & Action Protocol

When using `cpp-lint`, follow this logic to maximize success:

## 1. Analysis Phase

- **Locate Artifacts**: `cpp-lint` stores structured data (`report.json`,
  `report.sarif`, and `fixes/*.yaml`) inside the **`.lint` directory located in
  your Build Directory** (where `compile_commands.json` was found).
- **Read Data**: Always parse the `report.json` in the build dir for reliable
  diagnostic data.
- **Priority**: Fix `error` (environment) first, then `warning`.

## 2. Autonomous Action

- **Fast Fixes**: Prefer `cpp-lint --fix` over manual build system fix targets.
- **Auto-Formatting**: `cpp-lint` automatically runs `clang-format` after
  `--fix`. You don't need to format manually.
- **Missing Config**: If `.clang-format/tidy` are missing, copy from
  `assets/templates/` within the skill.

## 3. Verification

- **Re-run**: Always run `cpp-lint changed` after any fix to confirm
  resolution.

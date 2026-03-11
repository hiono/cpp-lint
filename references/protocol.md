# Agent Reasoning & Action Protocol

When using `cpp-lint`, follow this logic to maximize success:

## 1. Analysis Phase (Dry Run)

- **Execution**: Run `cpp-lint changed` (without `--fix`) to generate a dry run
  report.
- **Locate Artifacts**: `cpp-lint` stores structured data (`report.json`,
  `report.sarif`, and `fixes/*.yaml`) inside the **`.lint` directory located in
  your Build Directory** (where `compile_commands.json` was found).
- **Read Data**: Always parse the `report.json` in the build dir for reliable
  diagnostic data.

## 2. Advice Phase (Human-in-the-loop)

Before applying fixes, the agent should provide an **Advice Summary**:
- **Risk Assessment**: Identify `Safe` vs. `Manual Review` items.
- **Impact**: Estimate how many files/lines will change.
- **Recommendation**: Propose a specific action (e.g., "Apply safe fixes only").

## 3. Autonomous Action (Execution)

- **Fast Fixes**: Once agreed, run `cpp-lint --fix` for high-performance
  application.
- **Auto-Formatting**: `cpp-lint` automatically runs `clang-format` after
  `--fix`. You don't need to format manually.
- **Missing Config**: If `.clang-format/tidy` are missing, copy from
  `assets/templates/` within the skill.

## 4. Verification

- **Re-run**: Always run `cpp-lint changed` after any fix to confirm
  resolution.

## 5. jq Quick Reference (Surgical Triage)

To save tokens, use `jq` to query the `machine_report` instead of reading the
entire file:

```bash
# Count issues by severity
jq '.summary.issues' <machine_report>

# List unique files with warnings
jq '.issues[] | select(.severity == "warning") | .file' <machine_report> | sort | uniq

# Get all issues for a specific file
jq '.issues[] | select(.file == "src/main.cpp")' <machine_report>

# Show top 5 safe fix candidates
jq '.fixes | to_entries | .[:5]' <machine_report>
```



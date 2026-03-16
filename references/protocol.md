# Agent Reasoning & Action Protocol

When using \`cpp-lint\`, follow this logic to maximize success:

## 1. Analysis Phase (Dry Run)

- **Execution**: Run \`cpp-lint changed\` (without \`--fix\`) to generate a dry
  run report.
- **Locate Artifacts**: \`cpp-lint\` stores structured data (\`lint_report.json\`)
  inside the **\`cpp_lint_reports\` directory located in your Project Root**.
- **Manifest**: \`.cpp-lint-manifest.json\` contains absolute paths to all reports.
- **Read Data**: Always parse the \`lint_report.json\` for reliable diagnostic
  data.

## 2. Advice Phase (Human-in-the-loop)

Before applying fixes, the agent should provide an **Advice Summary**:

- **Risk Assessment**: Identify \`Safe\` vs. \`Manual Review\` items.
- **Impact**: Estimate how many files/lines will change.
- **Recommendation**: Propose a specific action (e.g., "Apply safe fixes only").

## 3. Autonomous Action (Execution)

- **Fast Fixes**: Once agreed, run \`cpp-lint --fix\` for high-performance
  application.
- **Auto-Formatting**: \`cpp-lint\` automatically runs \`clang-format\` after
  \`--fix\`.
- **Git-Set Filter**: Only files tracked by Git are processed.

## 4. Verification

- **Re-run**: Always run \`cpp-lint changed\` after any fix to confirm
  resolution.

## 5. jq Quick Reference (Surgical Triage)

To save tokens, use \`jq\` to query the \`machine_report\`:

\`\`\`bash
Count issues by severity
jq '.summary.issues' <machine_report>

List unique files with warnings
jq '.issues[] | select(.severity == "warning") | .file' <machine_report> \\
  | sort | uniq

Show only 'critical' checks
jq '.issues[] | select(.check | contains("VirtualCall"))' <machine_report>
\`\`\`

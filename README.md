# cpp-lint 🤖 [AI Agent Skill]

**AI Agent-native C++ Linting Pipeline.**

`cpp-lint` provides zero-setup, high-performance C++ code quality checks
powered by `clang-tidy`. Designed for autonomous AI agents with surgical
precision and structured reporting.

## 🌟 What Makes This a Skill

Unlike generic linting tools, `cpp-lint` is built specifically for AI agents:

- **Git-Native**: Only lints files tracked by Git. Ignores generated files,
  dependencies, and build artifacts automatically.
- **Agent-Ready**: Generates structured JSON/SARIF reports for autonomous
  reasoning and error recovery.
- **Surgical Precision**: Filters noise using path-based rules and Git status.
- **High-Performance**: Parallelized execution using Python ThreadPool.

## 🛠 Skill Installation

### Global (Recommended)

```bash
git clone https://github.com/hiono/cpp-lint ~/.agents/skills/cpp-lint
export PATH="$HOME/.agents/skills/cpp-lint/scripts:$PATH"
```

### Local (Project-Specific)

```bash
cd /path/to/your/project
git clone https://github.com/hiono/cpp-lint .agents/cpp-lint
```

## 📖 Usage

```bash
# Lint git-modified files (default)
./scripts/cpp-lint changed

# Lint all tracked files
./scripts/cpp-lint all

# Apply safe fixes and auto-format
./scripts/cpp-lint --fix
```

## 🔄 What's New in v0.2.0

- **Zero-Setup**: Now powered by `uv run` (PEP 723). Dependencies (Jinja2)
  installed automatically—no manual setup required.
- **Single-File**: Consolidated from Python + shell wrapper into single
  `cpp-lint` script.
- **Git-Native by Default**: Only lints files that are tracked by Git,
  eliminating noise from generated files.

## 📊 Outputs

| File | Description |
|------|-------------|
| `lint_report.md` | Human-readable summary with severity counts |
| `.lint/report.json` | Structured data for AI agent reasoning |
| `.lint/report.sarif` | SARIF format for IDE integration |

## 🤖 Reasoning Protocol

The agent follows the **[protocol.md](references/protocol.md)** to interpret
lint results and autonomously apply fixes.

Use `jq` to triage issues:

```bash
# Show only errors
jq '.issues[] | select(.severity == "error")' .lint/report.json

# Count by file
jq 'group_by(.file) | map({file: .[0].file, count: length})' .lint/report.json
```

---

Maintained by **hiono**. Distributed under the MIT License.

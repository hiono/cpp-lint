# cpp-lint

**AI Agent-Native C++ Linting Pipeline**

`cpp-lint` is a professional-grade C/C++ linting tool designed for modern development workflows where **Autonomous AI Agents** (Gemini CLI, Open Code, GitHub Copilot) collaborate with humans. It provides a deterministic `format → tidy` sequence with multi-threaded execution and multi-format reporting.

## 🚀 Key Advantages

- **Agent-Ready Architecture**: Beyond Markdown, it generates structured **JSON** and industry-standard **SARIF** reports, enabling AI agents to parse issues and apply fixes with 100% accuracy.
- **Surgical Performance**: Powered by a multi-threaded execution engine and `git ls-files` integration. Scans large-scale projects in seconds, not minutes.
- **Heuristic Discovery**: Automatically locates `compile_commands.json` across common build patterns (`build/`, `out/`, `target/`).
- **Clean Workspace Policy**: Artifacts (`.lint/`, SARIF, JSON) are stored within your build directory (`CMAKE_BINARY_DIR`), keeping your project root pristine.

---

## 🛠 Installation

### Global (Recommended)
Install once to use across all repositories:
```bash
mkdir -p ~/.agents/skills/
git clone https://github.com/hiono/cpp-lint ~/.agents/skills/cpp-lint
export PATH="$HOME/.agents/skills/cpp-lint/scripts:$PATH"
```

### Local (Project-specific)
```bash
mkdir -p .agents/skills/
# Extract cpp-lint.skill here
```

---

### Usage

#### Surgical Mode (Changed Files only)
Perfect for pre-commit checks. Targets staged, unstaged, and untracked files.
```bash
cpp-lint changed
```

#### Automatic Fixing (Replaces CMake tidy-fix)
Apply suggested fixes automatically. This is **8x faster** and safer than standard CMake targets.
```bash
cpp-lint changed --fix
# or for the full project
cpp-lint all --fix-errors
```

#### Full Audit
Performs a deep scan of the entire repository.
```bash
cpp-lint all
```

### Options
- `--fix`: Automatically apply suggested fixes.
- `--fix-errors`: Apply fixes even if compilation errors exist.
- `--skip-format`: Run static analysis without modifying code style.
- `-j N`, `--jobs N`: Set parallel worker count (defaults to CPU count).

---

## 🤖 Agent Protocol (For AI Users)

When an AI agent triggers this skill, it follows a built-in reasoning protocol:
1.  **Environment Sync**: Finds/syncs the Compilation Database automatically.
2.  **Surgical Analysis**: Runs linting and reads `.lint/report.json`.
3.  **Autonomous Fixing**: 
    - Applies `Safe` fixes via `.lint/apply_fixes.sh`.
    - Manually resolves complex issues (e.g., uninitialized variables) based on JSON diagnostics.
4.  **Verification**: Re-runs linting to verify the fix.

---

## 📦 Outputs

- `lint_report.md`: Human-readable executive summary (Root).
- `.lint/report.json`: Structured diagnostic data for AI Agents (Build Dir).
- `.lint/report.sarif`: Industry-standard format for GitHub Actions/IDEs (Build Dir).
- `.lint/fixes/*.yaml`: Exported clang-tidy replacements (Build Dir).

---

## ⚖️ License
Maintained by **hiono**. Distributed under the MIT License.
[github.com/hiono/cpp-lint](https://github.com/hiono/cpp-lint)

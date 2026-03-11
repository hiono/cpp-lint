# cpp-lint 🤖 [AI Agent Skill]

**High-Performance C++ Linting Pipeline built for Autonomous AI Agents.**

`cpp-lint` is not just a collection of scripts; it is a
**fully-fledged AI Agent Skill**. It equips agents (like Gemini, Claude, and
GitHub Copilot) with the procedural knowledge and multi-threaded tools needed
to analyze, format, and fix C++ code autonomously with expert-level precision.

---

## 🌟 What makes this a "Skill"?

Unlike a standard CLI tool, this package is designed for
**Machine-to-Machine interaction**:

- **Structured Reasoning**: Includes `SKILL.md` which defines a deterministic
  logic for agents to follow.
- **Agent-First Output**: Generates `.lint/report.json` specifically for AI
  parsing (saves tokens, increases accuracy).
- **Self-Healing Assets**: Provides `.clang-format/tidy` templates in `assets/`
  so the agent can fix a broken environment.
- **Universal Discovery**: Heuristically finds build databases so the agent
  doesn't need to ask "where is the build folder?".

---

## 🛠 Skill Installation

### 1. Global (Recommended for Personal AI)

Add to your global agent environment to use across all repositories:

```bash
git clone https://github.com/hiono/cpp-lint ~/.agents/skills/cpp-lint
# Ensure ~/.agents/skills is in your Agent's search path
```

### 2. Local (Project Scope)

Include this in your repository to give every AI Agent access to these
capabilities:

```bash
mkdir -p .agents/skills/
git submodule add https://github.com/hiono/cpp-lint .agents/skills/cpp-lint
```

---

## 📖 Agent Capabilities

When an agent is equipped with this skill, it can:

1. **`cpp-lint changed`**: Surgically scan only current modifications.
2. **`cpp-lint --fix`**: Automatically apply C++ best practices (Replaces
   standard build system fix targets).
3. **`cpp-lint all`**: Perform a full repository audit in seconds
   (Parallelized).

---

## 🤖 Reasoning Protocol

The agent follows the **[protocol.md](references/protocol.md)**:

1. **Analyze**: Read JSON diagnostics.
2. **Environment Sync**: Auto-discover `compile_commands.json`.
3. **Fix**: Apply safe fixes automatically (high-performance replacement for
   `clang-tidy -fix` targets); manually resolve complex bugs.
4. **Verify**: Re-run to confirm resolution.

---

## 📦 Outputs (For Agent & Human)

- `lint_report.md`: Human executive summary.
- `.lint/report.json`: AI-consumable structured data (Build Dir).
- `.lint/report.sarif`: Industry-standard integration (Build Dir).

---

## ⚖️ License

Maintained by **hiono**. Distributed under the MIT License.
[github.com/hiono/cpp-lint](https://github.com/hiono/cpp-lint)

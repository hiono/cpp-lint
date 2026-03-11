# cpp-lint

AI Agent-native C++ linting pipeline. Zero-setup, multi-threaded, and high-signal
reporting.

## Features

- **Zero-Setup**: Powered by \`uv run\` (PEP 723). Dependencies (Jinja2) are
  handled automatically.
- **Git-Native**: Only lints files tracked by Git. Pure signal, zero noise.
- **High-Performance**: Parallelized execution using Python ThreadPool.
- **Structured Reporting**: Generates Markdown, JSON, and SARIF.

## Usage

\`\`\`bash
./scripts/cpp-lint changed  # Lint git-modified files (default)
./scripts/cpp-lint all      # Lint all tracked files
./scripts/cpp-lint --fix    # Apply safe fixes and auto-format
\`\`\`

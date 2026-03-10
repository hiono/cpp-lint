# Details

## Scope
- `changed`: Targets files detected via `git diff --name-only` (staged + unstaged) and `git ls-files --others --exclude-standard` (untracked).
- `all`: Targets all files extracted via `git ls-files --cached --others --exclude-standard`. Directories ignored by `.gitignore` (such as `build/`) are excluded.

## Execution Order
1. **Sync compile_commands.json**: Searches for the latest compilation database from candidates like `build/` and syncs it to the project root.
2. **Apply clang-format**: Executes **mandatory `-i` (in-place)** formatting using `.clang-format` rules. This minimizes noise in subsequent static analysis.
3. **Execute clang-tidy**: Analyzes selected files and generates fix suggestions in YAML format via `-export-fixes`.
4. **Generate Reports**: Parses logs to create `lint_report.md` (for humans) and `.lint/report.json` (for machine processing).

## Fix Workflow
- Generated `.lint/fixes/*.yaml` files can be applied in bulk using the provided `.lint/apply_fixes.sh`.
- **Recommendation**: Always review changes via `git diff` before applying fixes to ensure intended behavior.

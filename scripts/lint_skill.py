#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "jinja2",
# ]
# ///
# -*- coding: utf-8 -*-

import argparse
import hashlib
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple
from jinja2 import Template

CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp"}
log_lock = threading.Lock()

@dataclass
class Issue:
    tool: str
    severity: str
    file: str
    line: int
    col: int
    check: str
    message: str

SAFE_FIX_ALLOW_PREFIX = ("readability-", "modernize-")
SAFE_FIX_DENY_EXACT = {"modernize-use-trailing-return-type"}

TIDY_RE = re.compile(r"^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+):\s+(?P<severity>warning|error|note):\s+(?P<message>.*?)(?:\s+\[(?P<check>[^\]]+)\])?\s*$")

# --- Reporting Template ---
MARKDOWN_TEMPLATE = """
# Lint Report ({{ timestamp }})

- **Scope**: `{{ scope }}`
- **Database**: {{ ccdb_msg }}

## Summary
- **Files Formatted/Fixed**: {{ formatted_count }}
- **Errors**: {{ sev_counts.error or 0 }}
- **Warnings**: {{ sev_counts.warning or 0 }}

### 📦 Detailed Artifacts
- Detailed data is in the build directory's `.lint/` folder.

{% if yaml_index %}
### Fixes: {{ yaml_index|length }} files (Safe: {{ safe_count }})
- Manual apply: Use `apply_fixes.sh` in the build dir.
{% endif %}

{% if issues %}
## Issues
| Sev | File | Line | Check | Message |
|---|---|---:|---|---|
{% for i in issues if i.severity != 'note' -%}
| {{ i.severity }} | `{{ i.rel_file }}` | {{ i.line }} | {{ i.check }} | {{ i.message }} |
{% endfor %}
{% endif %}
"""

def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def append_log(log_path: Path, text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_lock:
        with log_path.open("a", encoding="utf-8", errors="replace") as f: f.write(text)

def run_command(cmd: List[str], cwd: Path, log_path: Path) -> int:
    p = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
    append_log(log_path, f"\n\n## CMD: {' '.join(cmd)}\n{p.stdout}")
    return p.returncode

def get_project_relative_path(file_path: str, root: Path) -> str:
    try: return str(Path(file_path).resolve().relative_to(root.resolve()))
    except: return file_path

def pick_latest_compile_commands(project_root: Path) -> Optional[Path]:
    candidates = []
    try:
        out = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*compile_commands.json"], cwd=str(project_root), stderr=subprocess.DEVNULL, text=True)
        candidates = [project_root / line.strip() for line in out.splitlines() if line.strip()]
    except: pass
    if not candidates:
        for p in project_root.rglob("compile_commands.json"):
            if not any(part.startswith(".") for part in p.parts) and any(d in str(p) for d in {"build", "out", "target"}): candidates.append(p)
    if not candidates: return None
    candidates.sort(key=lambda p: (len(p.parts), -p.stat().st_mtime))
    return candidates[0]

def sync_compile_commands(project_root: Path) -> Tuple[bool, str, Optional[Path]]:
    src = pick_latest_compile_commands(project_root)
    if not src: return False, "compile_commands.json not found.", None
    dst = project_root / "compile_commands.json"
    if src.resolve() == dst.resolve(): return True, f"Latest DB already at root: {dst}", src.parent
    shutil.copy2(src, dst)
    return True, f"Synced latest DB: {src} -> {dst}", src.parent

def get_git_files(project_root: Path, scope: str) -> List[Path]:
    try:
        args = ["ls-files", "--cached", "--others", "--exclude-standard"] if scope == "all" else ["diff", "--name-only", "HEAD"]
        out = subprocess.check_output(["git"] + args, cwd=str(project_root), text=True)
        files = [project_root / l.strip() for l in out.splitlines() if l.strip()]
        return sorted([p for p in files if p.exists() and p.suffix.lower() in CPP_EXTS])
    except: return []

def get_all_project_files(project_root: Path) -> Set[str]:
    """Retrieves all tracked and untracked (non-ignored) files in the repo."""
    try:
        out = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=str(project_root), text=True)
        return {str((project_root / l.strip()).resolve()) for l in out.splitlines() if l.strip()}
    except: return set()

def parse_tidy_log(log_path: Path) -> List[Issue]:
    issues = []
    if not log_path.exists(): return issues
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TIDY_RE.match(line.strip())
        if m: issues.append(Issue(tool="clang-tidy", severity=m.group("severity"), file=m.group("file"), line=int(m.group("line")), col=int(m.group("col")), check=m.group("check") or "", message=m.group("message").strip()))
    return issues

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--scope", choices=["changed", "all"], default="changed")
    ap.add_argument("--jobs", "-j", type=int, default=multiprocessing.cpu_count())
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    os.chdir(str(root))
    log_path, report_path = Path("/tmp/lint.log"), root / "lint_report.md"
    if log_path.exists(): log_path.unlink()

    ok, ccdb_msg, build_dir = sync_compile_commands(root)
    if not ok: return 1

    lint_base = (build_dir or root) / ".lint"
    fixes_dir = lint_base / "fixes"
    for d in [lint_base, fixes_dir]: d.mkdir(parents=True, exist_ok=True)

    # Git-Native File Gathering
    files = get_git_files(root, args.scope)
    if not files: return 0
    project_files_set = get_all_project_files(root)

    modified_files: Set[Path] = set()
    def do_format(p):
        b = get_sha256(p)
        run_command(["clang-format", "-i", "-style=file"], root, log_path)
        return p if b != get_sha256(p) else None

    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        modified_files.update(r for r in ex.map(do_format, files) if r)

    tidy_cmd = ["clang-tidy", "-p", str(root)]
    if args.fix: tidy_cmd.append("-fix")
    for old in fixes_dir.glob("*.yaml"): old.unlink()

    def do_tidy(p):
        y = fixes_dir / (str(p.relative_to(root)).replace(os.sep, "__") + ".yaml")
        run_command(tidy_cmd + [str(p), f"-export-fixes={y}"], root, log_path)
        return (str(y.relative_to(root)), [l.split(":", 1)[1].strip().strip('"') for l in y.read_text().splitlines() if "DiagnosticName:" in l]) if y.exists() else ("", [])

    yaml_index = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r, d in ex.map(do_tidy, files):
            if r: yaml_index[r] = d

    if args.fix:
        try:
            subprocess.run(["clang-apply-replacements", str(fixes_dir)], check=True, capture_output=True)
            with ThreadPoolExecutor(max_workers=args.jobs) as ex: modified_files.update(r for r in ex.map(do_format, files) if r)
        except: pass

    # SURGICAL FILTER: Only keep issues belonging to Git-tracked/untracked files
    raw_issues = parse_tidy_log(log_path)
    issues = [i for i in raw_issues if str(Path(i.file).resolve()) in project_files_set]
    for i in issues: i.rel_file = get_project_relative_path(i.file, root)
    
    sev_counts = {s: sum(1 for i in issues if i.severity == s) for s in ["error", "warning"]}
    safe_count = sum(1 for d in yaml_index.values() if any(x.startswith(("readability-", "modernize-")) for x in d))
    
    report_md = Template(MARKDOWN_TEMPLATE).render(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), scope=args.scope, ccdb_msg=ccdb_msg, formatted_count=len(modified_files), sev_counts=sev_counts, issues=issues, yaml_index=yaml_index, safe_count=safe_count)
    report_path.write_text(report_md, encoding="utf-8")
    
    summary = {"quick_ref": {"formatted": len(modified_files), "errors": sev_counts["error"], "warnings": sev_counts["warning"]}, "artifacts": {"machine_report": str((lint_base / "lint_report.json").resolve())}}
    (lint_base / "lint_report.json").write_text(json.dumps({"metadata": {"scope": args.scope}, "summary": summary["quick_ref"], "issues": [asdict(i) for i in issues]}, indent=2))
    print(json.dumps(summary, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())

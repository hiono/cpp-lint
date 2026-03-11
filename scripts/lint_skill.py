#!/usr/bin/env python3
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
from typing import Dict, List, Optional, Tuple

CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp"}

# Global lock for thread-safe logging
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


SAFE_FIX_ALLOW_PREFIX = (
    "readability-",
    "modernize-",
)
SAFE_FIX_DENY_EXACT = {
    "modernize-use-trailing-return-type",
}

TIDY_RE = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<severity>warning|error|note):\s+"
    r"(?P<message>.*?)(?:\s+\[(?P<check>[^\]]+)\])?\s*$"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def append_log(log_path: Path, text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_lock:
        with log_path.open("a", encoding="utf-8", errors="replace") as f:
            f.write(text)


def run(cmd: List[str], cwd: Path, log_path: Path) -> int:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    append_log(log_path, f"\n\n## CMD: {' '.join(cmd)}\n{p.stdout}")
    return p.returncode


def pick_latest_compile_commands(project_root: Path) -> Optional[Path]:
    candidates: List[Path] = []
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*compile_commands.json"],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        candidates = [project_root / line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        pass

    if not candidates:
        common_dirs = {"build", "out", "target", "bin", "Debug", "Release"}
        for p in project_root.rglob("compile_commands.json"):
            if not any(part.startswith(".") for part in p.parts):
                if any(d in str(p) for d in common_dirs):
                    candidates.append(p)

    if not candidates:
        return None

    candidates.sort(key=lambda p: (len(p.parts), -p.stat().st_mtime))
    return candidates[0]


def sync_compile_commands(project_root: Path) -> Tuple[bool, str, Optional[Path]]:
    src = pick_latest_compile_commands(project_root)
    if src is None:
        msg = (
            "ERROR: compile_commands.json not found.\n"
            "Run: cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON . OR cmake --preset dev"
        )
        return False, msg, None
    dst = project_root / "compile_commands.json"
    if src.resolve() == dst.resolve():
        return True, f"Latest DB already at root: {dst}", src.parent
    shutil.copy2(src, dst)
    return True, f"Synced latest DB: {src} -> {dst}", src.parent


def is_source_file(p: Path) -> bool:
    return p.suffix.lower() in CPP_EXTS


def git_list_files_all(project_root: Path) -> List[Path]:
    files: List[Path] = []
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        files = [project_root / line.strip() for line in out.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if not files:
        for ext in CPP_EXTS:
            for p in project_root.rglob(f"*{ext}"):
                if p.is_file() and not any(part.startswith(".") for part in p.parts):
                    files.append(p)

    return sorted(list(set(p for p in files if p.is_file() and is_source_file(p))))


def git_list_files_changed(project_root: Path) -> List[Path]:
    def _run_git(args: List[str]) -> List[str]:
        try:
            out = subprocess.check_output(["git"] + args, cwd=str(project_root), text=True)
            return [x.strip() for x in out.splitlines() if x.strip()]
        except subprocess.CalledProcessError:
            return []

    staged = _run_git(["diff", "--name-only", "--cached"])
    unstaged = _run_git(["diff", "--name-only"])
    untracked = _run_git(["ls-files", "--others", "--exclude-standard"])

    names = sorted(set(staged + unstaged + untracked))
    files = [project_root / n for n in names]
    return [p for p in files if p.exists() and is_source_file(p)]


def ensure_lint_dirs(base_path: Path) -> Tuple[Path, Path]:
    base = base_path / ".lint"
    fixes = base / "fixes"
    base.mkdir(parents=True, exist_ok=True)
    fixes.mkdir(parents=True, exist_ok=True)
    return base, fixes


def safe_yaml_name(project_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(project_root)
    return str(rel).replace("/", "__") + ".yaml"


def parse_tidy_log(log_path: Path) -> List[Issue]:
    issues: List[Issue] = []
    if not log_path.exists():
        return issues

    for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip("\n")
        m = TIDY_RE.match(line)
        if m:
            issues.append(
                Issue(
                    tool="clang-tidy",
                    severity=m.group("severity"),
                    file=m.group("file"),
                    line=int(m.group("line")),
                    col=int(m.group("col")),
                    check=m.group("check") or "",
                    message=m.group("message").strip(),
                )
            )
    return issues


def extract_diagnostic_names_from_yaml(yaml_path: Path) -> List[str]:
    names: List[str] = []
    if not yaml_path.exists():
        return names
    for line in yaml_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("DiagnosticName:"):
            v = line.split(":", 1)[1].strip().strip('"')
            if v:
                names.append(v)
    return names


def is_safe_diagnostic(name: str) -> bool:
    if name in SAFE_FIX_DENY_EXACT:
        return False
    return any(name.startswith(p) for p in SAFE_FIX_ALLOW_PREFIX)


def write_apply_script(lint_base: Path) -> Path:
    path = lint_base / "apply_fixes.sh"
    content = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'FIXDIR="$(dirname "${BASH_SOURCE[0]}")/fixes"\n\n'
        'for y in "$FIXDIR"/*.yaml; do\n'
        '  [ -e "$y" ] || continue\n'
        '  clang-apply-replacements "$y"\n'
        "done\n"
    )
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o755)
    return path


def to_markdown(
    issues: List[Issue],
    project_root: Path,
    scope: str,
    formatted_files: List[Path],
    ccdb_msg: str,
    yaml_index: Dict[str, List[str]],
    safe_yaml_files: List[str],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    has_format_cfg = (project_root / ".clang-format").exists()
    has_tidy_cfg = (project_root / ".clang-tidy").exists()

    sev_counts: Dict[str, int] = {}
    for it in issues:
        sev_counts[it.severity] = sev_counts.get(it.severity, 0) + 1

    lines = [f"# Lint Report ({now})", f"- Scope: `{scope}`", f"- DB: {ccdb_msg}", ""]

    if not has_format_cfg or not has_tidy_cfg:
        lines.append("### ⚠️ Config Missing")
        if not has_format_cfg:
            lines.append("- `.clang-format` missing. Run `clang-format -style=llvm -dump-config > .clang-format`")
        if not has_tidy_cfg:
            lines.append("- `.clang-tidy` missing. Run `clang-tidy -dump-config > .clang-tidy`")
        lines.append("")

    lines.append(f"## Format: {len(formatted_files)} files updated")
    lines.append(f"## Tidy: {sev_counts.get('error', 0)} errors, {sev_counts.get('warning', 0)} warnings")
    lines.append("")

    if yaml_index:
        lines.append(f"### Fixes: {len(yaml_index)} files (Safe: {len(safe_yaml_files)})")
        lines.append("- Apply: `bash .lint/apply_fixes.sh` (Check location in build dir)")
        lines.append("")

    if issues:
        lines.append("## Issues")
        lines.append("| Sev | File | Line | Check | Message |")
        lines.append("|---|---|---:|---|---|")

        def relpath(s: str) -> str:
            try:
                return str(Path(s).resolve().relative_to(project_root.resolve()))
            except Exception:
                return s

        issues_sorted = sorted(
            issues,
            key=lambda x: ({"error": 0, "warning": 1, "note": 2}.get(x.severity, 9), relpath(x.file), x.line),
        )
        for it in issues_sorted:
            if it.severity == "note":
                continue
            lines.append(f"| {it.severity} | `{relpath(it.file)}` | {it.line} | {it.check} | {it.message} |")
    return "\n".join(lines)


def to_json(
    issues: List[Issue],
    project_root: Path,
    scope: str,
    formatted_files: List[Path],
    ccdb_msg: str,
    yaml_index: Dict[str, List[str]],
) -> str:
    res = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "scope": scope,
            "config": {
                "has_clang_format": (project_root / ".clang-format").exists(),
                "has_clang_tidy": (project_root / ".clang-tidy").exists(),
            },
        },
        "summary": {"formatted_count": len(formatted_files), "issues": {}},
        "issues": [asdict(i) for i in issues],
        "fixes": yaml_index,
    }
    for it in issues:
        res["summary"]["issues"][it.severity] = res["summary"]["issues"].get(it.severity, 0) + 1
    return json.dumps(res, indent=2, ensure_ascii=False)


def to_sarif(issues: List[Issue], project_root: Path) -> str:
    def relpath(s: str) -> str:
        try:
            return str(Path(s).resolve().relative_to(project_root.resolve()))
        except Exception:
            return s

    results = []
    for it in issues:
        level = "warning"
        if it.severity == "error":
            level = "error"
        elif it.severity == "note":
            level = "note"
        results.append(
            {
                "ruleId": it.check,
                "level": level,
                "message": {"text": it.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": relpath(it.file)},
                            "region": {"startLine": it.line, "startColumn": it.col},
                        }
                    }
                ],
            }
        )
    return json.dumps(
        {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "clang-tidy"}}, "results": results}],
        },
        indent=2,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--scope", choices=["changed", "all"], default="changed")
    ap.add_argument("--log", default="/tmp/lint.log")
    ap.add_argument("--report", default="lint_report.md")
    ap.add_argument("--no-sync-ccdb", action="store_true")
    ap.add_argument("--skip-format", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--fix-errors", action="store_true")
    ap.add_argument("--jobs", "-j", type=int, default=multiprocessing.cpu_count())
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    log_path = Path(args.log).resolve()
    report_path = (project_root / args.report).resolve()

    if log_path.exists():
        log_path.unlink()

    ccdb_msg = "skipped"
    build_dir = project_root
    if not args.no_sync_ccdb:
        ok, msg, found_build_dir = sync_compile_commands(project_root)
        ccdb_msg = msg
        if found_build_dir:
            build_dir = found_build_dir
        append_log(log_path, f"## DB sync: {msg}\n")
        if not ok:
            report_path.write_text(f"# FAILED\n\n{msg}\n")
            print(str(report_path))
            return 1

    lint_base, fixes_dir = ensure_lint_dirs(build_dir)
    files = git_list_files_all(project_root) if args.scope == "all" else git_list_files_changed(project_root)
    if not files:
        report_path.write_text("# No target files\n")
        print(str(report_path))
        return 0

    # (C1) Format
    formatted_files = []
    if not args.skip_format:
        fmt_cmd = ["clang-format", "-i", "-style=file"]

        def do_format(p):
            b = sha256(p)
            run(fmt_cmd + [str(p)], project_root, log_path)
            return p if b != sha256(p) else None

        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            formatted_files = [r for r in ex.map(do_format, files) if r]

    # (C2) Tidy
    tidy_cmd = ["clang-tidy", "-p", str(project_root)]
    if args.fix_errors:
        tidy_cmd.append("-fix-errors")
    elif args.fix:
        tidy_cmd.append("-fix")

    yaml_index = {}
    for old in fixes_dir.glob("*.yaml"):
        old.unlink()

    def do_tidy(p):
        y = fixes_dir / safe_yaml_name(project_root, p)
        run(tidy_cmd + [str(p), f"-export-fixes={y}"], project_root, log_path)
        return (str(y.relative_to(project_root)), extract_diagnostic_names_from_yaml(y)) if y.exists() else ("", [])

    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r, d in ex.map(do_tidy, files):
            if r:
                yaml_index[r] = d

    write_apply_script(lint_base)
    if args.fix or args.fix_errors:
        try:
            subprocess.run(["clang-apply-replacements", str(fixes_dir)], check=True, capture_output=True)
            # Re-format after fixes to clean up the code
            if not args.skip_format:
                append_log(log_path, "\n## Re-formatting after fixes\n")
                fmt_cmd = ["clang-format", "-i", "-style=file"]
                with ThreadPoolExecutor(max_workers=args.jobs) as ex:
                    list(ex.map(lambda p: run(fmt_cmd + [str(p)], project_root, log_path), files))
        except Exception:
            pass

    issues = parse_tidy_log(log_path)
    safe_yaml = [r for r, d in yaml_index.items() if any(is_safe_diagnostic(x) for x in d)]

    md = to_markdown(issues, project_root, args.scope, formatted_files, ccdb_msg, yaml_index, safe_yaml)
    if args.skip_format:
        md = md.replace("## Format", "## Format (Skipped)")
    report_path.write_text(md, encoding="utf-8")
    (lint_base / "report.json").write_text(to_json(issues, project_root, args.scope, formatted_files, ccdb_msg, yaml_index))
    (lint_base / "report.sarif").write_text(to_sarif(issues, project_root))

    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

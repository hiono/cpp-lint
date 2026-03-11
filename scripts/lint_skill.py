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
from typing import Dict, List, Optional, Set, Tuple

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

TIDY_RE = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<severity>warning|error|note):\s+"
    r"(?P<message>.*?)(?:\s+\[(?P<check>[^\]]+)\])?\s*$"
)


def get_sha256(path: Path) -> str:
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


def run_command(cmd: List[str], cwd: Path, log_path: Path) -> int:
    p = subprocess.run(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    append_log(log_path, f"\n\n## CMD: {' '.join(cmd)}\n{p.stdout}")
    return p.returncode


def get_project_relative_path(file_path: str, root: Path) -> str:
    try:
        abs_file = Path(file_path).resolve()
        return str(abs_file.relative_to(root.resolve()))
    except (ValueError, RuntimeError):
        return file_path


def pick_latest_compile_commands(project_root: Path) -> Optional[Path]:
    """Heuristically discovers the most relevant compile_commands.json."""
    candidates: List[Path] = []
    try:
        out = subprocess.check_output(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "*compile_commands.json",
            ],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        candidates = [
            project_root / line.strip() for line in out.splitlines() if line.strip()
        ]
    except Exception:
        pass

    if not candidates:
        noise_dirs = {"build", "out", "target", "bin", "Debug", "Release"}
        for p in project_root.rglob("compile_commands.json"):
            if not any(part.startswith(".") for part in p.parts) and any(
                d in str(p) for d in noise_dirs
            ):
                candidates.append(p)

    if not candidates:
        return None

    candidates.sort(key=lambda p: (len(p.parts), -p.stat().st_mtime))
    return candidates[0]


def sync_compile_commands(project_root: Path) -> Tuple[bool, str, Optional[Path]]:
    src = pick_latest_compile_commands(project_root)
    if not src:
        msg = "ERROR: compile_commands.json not found.\nRun: cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON . OR cmake --preset dev"
        return False, msg, None

    dst = project_root / "compile_commands.json"
    if src.resolve() == dst.resolve():
        return True, f"Latest DB already at root: {dst}", src.parent

    shutil.copy2(src, dst)
    return True, f"Synced latest DB: {src} -> {dst}", src.parent


def is_source_file(p: Path) -> bool:
    return p.suffix.lower() in CPP_EXTS


def get_git_files(project_root: Path, scope: str) -> List[Path]:
    if scope == "all":
        try:
            out = subprocess.check_output(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                cwd=str(project_root),
                stderr=subprocess.DEVNULL,
                text=True,
            )
            files = [
                project_root / line.strip() for line in out.splitlines() if line.strip()
            ]
            return sorted([p for p in files if p.is_file() and is_source_file(p)])
        except Exception:
            return sorted(
                [
                    p
                    for p in project_root.rglob("*")
                    if p.is_file()
                    and is_source_file(p)
                    and not any(part.startswith(".") for part in p.parts)
                ]
            )

    def run_git(args: List[str]) -> List[str]:
        try:
            out = subprocess.check_output(
                ["git"] + args, cwd=str(project_root), text=True
            )
            return [x.strip() for x in out.splitlines() if x.strip()]
        except Exception:
            return []

    staged, unstaged, untracked = (
        run_git(["diff", "--name-only", "--cached"]),
        run_git(["diff", "--name-only"]),
        run_git(["ls-files", "--others", "--exclude-standard"]),
    )
    names = sorted(set(staged + unstaged + untracked))
    return [
        project_root / n
        for n in names
        if (project_root / n).exists() and is_source_file(project_root / n)
    ]


def ensure_lint_dirs(base_path: Path) -> Tuple[Path, Path]:
    base = base_path / ".lint"
    fixes = base / "fixes"
    base.mkdir(parents=True, exist_ok=True)
    fixes.mkdir(parents=True, exist_ok=True)
    return base, fixes


def parse_tidy_log(log_path: Path) -> List[Issue]:
    issues = []
    if not log_path.exists():
        return issues
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TIDY_RE.match(line.strip())
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


def get_safe_yaml_name(project_root: Path, file_path: Path) -> str:
    return str(file_path.relative_to(project_root)).replace(os.sep, "__") + ".yaml"


def extract_diagnostic_names(yaml_path: Path) -> List[str]:
    names = []
    if not yaml_path.exists():
        return names
    for line in yaml_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("DiagnosticName:"):
            v = line.split(":", 1)[1].strip().strip('"')
            if v:
                names.append(v)
    return names


def is_safe_diagnostic(name: str) -> bool:
    return (
        any(name.startswith(p) for p in SAFE_FIX_ALLOW_PREFIX)
        and name not in SAFE_FIX_DENY_EXACT
    )


def write_apply_script(lint_base: Path) -> Path:
    path = lint_base / "apply_fixes.sh"
    content = '#!/usr/bin/env bash\nset -euo pipefail\nFIXDIR="$(dirname "${BASH_SOURCE[0]}")/fixes"\nfor y in "$FIXDIR"/*.yaml; do\n  [ -e "$y" ] || continue\n  clang-apply-replacements "$y"\ndone\n'
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o755)
    return path


def generate_markdown(
    issues: List[Issue],
    project_root: Path,
    scope: str,
    formatted_files: Set[Path],
    ccdb_msg: str,
    yaml_index: Dict[str, List[str]],
    safe_yaml_files: List[str],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    has_format_cfg, has_tidy_cfg = (
        (project_root / ".clang-format").exists(),
        (project_root / ".clang-tidy").exists(),
    )
    sev_counts = {
        s: sum(1 for i in issues if i.severity == s)
        for s in ["error", "warning", "note"]
    }

    lines = [f"# Lint Report ({now})", f"- Scope: `{scope}`", f"- DB: {ccdb_msg}", ""]
    if not has_format_cfg or not has_tidy_cfg:
        lines.append("### ⚠️ Config Missing")
        if not has_format_cfg:
            lines.append(
                "- `.clang-format` missing. Run `clang-format -style=llvm -dump-config > .clang-format`"
            )
        if not has_tidy_cfg:
            lines.append(
                "- `.clang-tidy` missing. Run `clang-tidy -dump-config > .clang-tidy`"
            )
        lines.append("")

    lines.extend(
        [
            f"## Summary: {len(formatted_files)} files formatted/fixed",
            f"## Tidy: {sev_counts['error']} errors, {sev_counts['warning']} warnings",
            "",
            "### 📦 Detailed Artifacts",
            "- Structured data (`report.json`, `report.sarif`) and manual fixes (`fixes/*.yaml`) are stored in the build directory's `.lint/` folder.",
            "",
        ]
    )
    if yaml_index:
        lines.extend(
            [
                f"### Fixes: {len(yaml_index)} files (Safe: {len(safe_yaml_files)})",
                "- Manual apply: Look for `apply_fixes.sh` inside the `.lint` directory in your build folder.",
                "",
            ]
        )

    if issues:
        lines.extend(
            [
                "## Issues",
                "| Sev | File | Line | Check | Message |",
                "|---|---|---:|---|---|",
            ]
        )
        for it in sorted(
            issues,
            key=lambda x: (
                {"error": 0, "warning": 1, "note": 2}.get(x.severity, 9),
                get_project_relative_path(x.file, project_root),
                x.line,
            ),
        ):
            if it.severity != "note":
                lines.append(
                    f"| {it.severity} | `{get_project_relative_path(it.file, project_root)}` | {it.line} | {it.check} | {it.message} |"
                )
    return "\n".join(lines)


def generate_json(
    issues: List[Issue],
    project_root: Path,
    scope: str,
    formatted_files: Set[Path],
    ccdb_msg: str,
    yaml_index: Dict[str, List[str]],
) -> str:
    return json.dumps(
        {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "scope": scope,
                "project_root": str(project_root.resolve()),
                "config": {
                    "has_clang_format": (project_root / ".clang-format").exists(),
                    "has_clang_tidy": (project_root / ".clang-tidy").exists(),
                },
            },
            "summary": {
                "formatted_count": len(formatted_files),
                "issues": {
                    s: sum(1 for i in issues if i.severity == s)
                    for s in ["error", "warning", "note"]
                },
            },
            "issues": [asdict(i) for i in issues],
            "fixes": yaml_index,
        },
        indent=2,
        ensure_ascii=False,
    )


def generate_sarif(issues: List[Issue], project_root: Path) -> str:
    results = [
        {
            "ruleId": i.check,
            "level": {"error": "error", "note": "note"}.get(i.severity, "warning"),
            "message": {"text": i.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": get_project_relative_path(i.file, project_root)
                        },
                        "region": {"startLine": i.line, "startColumn": i.col},
                    }
                }
            ],
        }
        for i in issues
    ]
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
    os.chdir(str(project_root))
    log_path, report_path = (
        Path(args.log).resolve(),
        (project_root / args.report).resolve(),
    )
    if log_path.exists():
        log_path.unlink()

    ccdb_msg, build_dir = "skipped", project_root
    if not args.no_sync_ccdb:
        ok, msg, found_dir = sync_compile_commands(project_root)
        ccdb_msg, build_dir = msg, found_dir or project_root
        append_log(log_path, f"## DB sync: {msg}\n")
        if not ok:
            report_path.write_text(f"# FAILED\n\n{msg}\n")
            print(str(report_path))
            return 1

    lint_base, fixes_dir = ensure_lint_dirs(build_dir)
    files = get_git_files(project_root, args.scope)
    if not files:
        report_path.write_text("# No target files\n")
        print(str(report_path))
        return 0

    modified_files: Set[Path] = set()

    def do_format(p):
        b = get_sha256(p)
        run_command(["clang-format", "-i", "-style=file"], project_root, log_path)
        return p if b != get_sha256(p) else None

    if not args.skip_format:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            modified_files.update(r for r in ex.map(do_format, files) if r)

    tidy_cmd = ["clang-tidy", "-p", str(project_root)]
    if args.fix_errors:
        tidy_cmd.append("-fix-errors")
    elif args.fix:
        tidy_cmd.append("-fix")

    for old in fixes_dir.glob("*.yaml"):
        old.unlink()

    def do_tidy(p):
        y = fixes_dir / get_safe_yaml_name(project_root, p)
        run_command(tidy_cmd + [str(p), f"-export-fixes={y}"], project_root, log_path)
        return (
            (str(y.relative_to(project_root)), extract_diagnostic_names(y))
            if y.exists()
            else ("", [])
        )

    yaml_index = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r, d in ex.map(do_tidy, files):
            if r:
                yaml_index[r] = d

    write_apply_script(lint_base)
    if args.fix or args.fix_errors:
        try:
            subprocess.run(
                ["clang-apply-replacements", str(fixes_dir)],
                check=True,
                capture_output=True,
            )
            if not args.skip_format:
                with ThreadPoolExecutor(max_workers=args.jobs) as ex:
                    modified_files.update(r for r in ex.map(do_format, files) if r)
        except Exception as e:
            append_log(log_path, f"ERROR applying fixes: {e}\n")

    def is_project_source(f: str) -> bool:
        try:
            rel = Path(os.path.abspath(f)).relative_to(project_root)
            return not any(
                p
                in {
                    "build",
                    "out",
                    "target",
                    "bin",
                    "vcpkg",
                    "_deps",
                    "external",
                    "vendor",
                }
                for p in rel.parts
            )
        except ValueError:
            return False

    issues = [i for i in parse_tidy_log(log_path) if is_project_source(i.file)]
    safe_yaml = [
        r for r, d in yaml_index.items() if any(is_safe_diagnostic(x) for x in d)
    ]

    report_path.write_text(
        generate_markdown(
            issues,
            project_root,
            args.scope,
            modified_files,
            ccdb_msg,
            yaml_index,
            safe_yaml,
        ),
        encoding="utf-8",
    )
    (lint_base / "report.json").write_text(
        generate_json(
            issues, project_root, args.scope, modified_files, ccdb_msg, yaml_index
        )
    )
    (lint_base / "report.sarif").write_text(generate_sarif(issues, project_root))

    # Final concise output for Token efficiency
    summary = {
        "quick_ref": {
            "formatted_count": len(modified_files),
            "errors": sum(1 for i in issues if i.severity == "error"),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
        },
        "artifacts": {
            "human_report": str(report_path),
            "machine_report": str((lint_base / "report.json").resolve()),
            "sarif_report": str((lint_base / "report.sarif").resolve()),
        },
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

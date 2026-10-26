#!/usr/bin/env python3
"""Idempotent, non-destructive ApexSVC compatibility patch installer.

Git apply --reverse --check normally returns exit code 1 on unpatched files:
this is NOT an installation failure. The old PowerShell 5.1 wrapper treated
Git diagnostic stderr as a terminating NativeCommandError before it could
check that exit code.

This tool captures stderr, separates each trusted file patch, preflights ALL
targets, and applies only the missing parts. It never git-resets, deletes
checkpoints, or overwrites a conflicting user modification.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ALLOWED_PATHS = frozenset((
    "svc/content/encoder.py",
    "svc/content/wavlm/WavLM.py",
    "svc/pipeline.py",
))


@dataclass(frozen=True)
class PatchPart:
    path: str
    data: bytes


def checked_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, check=False
    )


def git_error(result: subprocess.CompletedProcess) -> str:
    raw = result.stderr or result.stdout or b""
    return raw.decode("utf-8", "replace").strip()[-650:] or "Git returned exit code %d" % result.returncode


def load_sections(source: Path) -> list[PatchPart]:
    raw = source.read_bytes().replace(b"\r\n", b"\n")
    lines = raw.splitlines(keepends=True)
    sections: list[bytes] = []
    buf: list[bytes] = []
    for line in lines:
        if line.startswith(b"diff --git "):
            if buf:
                sections.append(b"".join(buf))
            buf = [line]
        elif buf:
            buf.append(line)
        elif line.strip():
            raise ValueError("Unexpected content before Git patch header")
    if buf:
        sections.append(b"".join(buf))
    if not sections:
        raise ValueError("Patch file is empty")
    found: set[str] = set()
    out: list[PatchPart] = []
    for chunk in sections:
        head = chunk.split(b"\n", 1)[0].decode("utf-8", "replace")
        match = re.fullmatch(r"diff --git a/(.+) b/(.+)", head)
        if not match or match.group(1) != match.group(2):
            raise ValueError("Unexpected patch target: " + head)
        path = match.group(1)
        if path not in ALLOWED_PATHS or path in found:
            raise ValueError("Unapproved or duplicate patch target: " + path)
        if b"\n--- a/" not in chunk or b"\n+++ b/" not in chunk or b"\n@@ " not in chunk:
            raise ValueError("Incomplete unified diff for " + path)
        found.add(path)
        out.append(PatchPart(path, chunk if chunk.endswith(b"\n") else chunk + b"\n"))
    if found != ALLOWED_PATHS:
        raise ValueError("ApexSVC patch is missing one or more expected source files")
    return out


def execute(repo: Path, patch_file: Path, expected_commit: str) -> tuple[int, int]:
    repo = repo.resolve(strict=True)
    patch_file = patch_file.resolve(strict=True)
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("Expected Git commit must be a 40-character SHA-1")
    if not (repo / ".git").exists():
        raise RuntimeError("ApexSVC folder is not a Git checkout: " + str(repo))
    current = checked_git(repo, "rev-parse", "HEAD")
    if current.returncode or current.stdout.decode().strip() != expected_commit:
        raise RuntimeError("Wrong ApexSVC Git commit; refusing to patch non-pinned source")
    sections = load_sections(patch_file)
    with tempfile.TemporaryDirectory(prefix="hapych-apex-patch-") as work:
        action: list[tuple[PatchPart, Path, str]] = []
        for idx, section in enumerate(sections):
            target = repo / section.path
            if not target.is_file() or target.is_symlink():
                raise RuntimeError("ApexSVC target is missing or a symbolic link: " + section.path)
            # Git apply requires patch context to match the checked-out
            # source newline style. Windows core.autocrlf may create CRLF
            # files even though the published patch is LF. Switching the
            # entire repo to core.autocrlf=true would rewrite LF sources;
            # using --ignore-whitespace could introduce mixed endings.
            # Instead build only an ephemeral per-file patch with the
            # exact existing newline style, preserving all untouched bytes.
            content = target.read_bytes()
            line_count = content.count(b"\n")
            crlf_count = content.count(b"\r\n")
            if crlf_count not in (0, line_count):
                raise RuntimeError(
                    "ApexSVC target has mixed LF and CRLF line endings: "
                    + section.path + ". Refusing to rewrite the file."
                )
            patch_bytes = section.data.replace(b"\n", b"\r\n") if crlf_count else section.data
            isolated = Path(work) / ("part_%02d.patch" % idx)
            isolated.write_bytes(patch_bytes)
            reversed_check = checked_git(repo, "apply", "--reverse", "--check", str(isolated))
            if reversed_check.returncode == 0:
                action.append((section, isolated, "already"))
                continue
            forward_check = checked_git(repo, "apply", "--check", str(isolated))
            if forward_check.returncode == 0:
                action.append((section, isolated, "pending"))
                continue
            # Abort before modifying ANY file, even when some targets were
            # already patched. This preserves all user edits and prior models.
            raise RuntimeError(
                "ApexSVC patch conflict in %s. Existing files were not changed by "
                "this run. Reverse check: %s; forward check: %s. "
                "Do not delete the folder. See docs/TROUBLESHOOTING.md."
                % (section.path, git_error(reversed_check), git_error(forward_check))
            )
        applied = 0
        already = 0
        for section, isolated, status in action:
            if status == "already":
                print("APEX_ALREADY_PATCHED " + section.path, flush=True)
                already += 1
                continue
            result = checked_git(repo, "apply", str(isolated))
            if result.returncode:
                raise RuntimeError(
                    "ApexSVC patch could not be applied to %s: %s. "
                    "No files were reset or deleted." % (section.path, git_error(result))
                )
            if checked_git(repo, "apply", "--reverse", "--check", str(isolated)).returncode:
                raise RuntimeError("ApexSVC patch verification failed after applying " + section.path)
            print("APEX_APPLIED " + section.path, flush=True)
            applied += 1
    print("APEX_PATCH_OK applied=%d already_applied=%d" % (applied, already), flush=True)
    return applied, already


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    try:
        execute(args.repo, args.patch, args.expected_commit)
    except (OSError, ValueError, RuntimeError) as exc:
        print("APEX_PATCH_FAILED: " + str(exc), file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""ApexSVC installer regression tests, using disposable synthetic repositories.

Builds minimal synthetic upstream files from the already-public unified
diff's context (no third-party pretrained models or network downloads).
Never touches the real installed ApexSVC repository.
"""
from __future__ import annotations

import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from apply_apex_patch import execute, load_sections

PATCH = ROOT / "overlays" / "apexsvc_custom.patch"


def git(root: Path, *parts: str) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", "-C", str(root), *parts], text=True,
                            capture_output=True, check=False)
    if result.returncode != 0:
        raise AssertionError("git failed: %s\n%s" % (" ".join(parts), result.stderr[-500:]))
    return result


def fixture(root: Path) -> str:
    root.mkdir(parents=True)
    git(root, "init", "-q")
    git(root, "config", "user.email", "ci@example.invalid")
    git(root, "config", "user.name", "HAPYCH Installer QA")
    git(root, "config", "core.autocrlf", "false")
    for part in load_sections(PATCH):
        match = re.search(rb"(?m)^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", part.data)
        if not match:
            raise AssertionError("Invalid unified hunk in %s" % part.path)
        start = int(match.group(1))
        tail = part.data[match.end():].split(b"\n", 1)[1]
        old_context = []
        for line in tail.splitlines(keepends=True):
            if line.startswith((b" ", b"-")):
                old_context.append(line[1:])
            elif line.startswith((b"+", b"\\")):
                continue
            elif line.strip():
                raise AssertionError("Unexpected diff line: " + repr(line))
        data = b"# fixture filler line\n" * (start - 1) + b"".join(old_context)
        data += b"# more fixture context\n" * 5
        target = root / part.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    git(root, "add", ".")
    git(root, "commit", "-qm", "Minimal synthetic upstream")
    return git(root, "rev-parse", "HEAD").stdout.strip()


def apply_one(root: Path, i: int, temp_root: Path) -> None:
    part = load_sections(PATCH)[i]
    file = temp_root / ("only-%d.patch" % i)
    file.write_bytes(part.data)
    git(root, "apply", str(file))


def files_snapshot(root: Path) -> dict[str, bytes]:
    return {p.path: (root / p.path).read_bytes() for p in load_sections(PATCH)}


class TestApexPatch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hapych-apex-compat-QA-")
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.root = self.scratch / "fake ApexSVC repository with spaces"
        self.sha = fixture(self.root)

    def test_clean_checkout_applies_all_three_files(self):
        applied, previously = execute(self.root, PATCH, self.sha)
        self.assertEqual((applied, previously), (3, 0))
        self.assertEqual(len(git(self.root, "status", "--porcelain").stdout.splitlines()), 3)

    def test_second_run_skips_already_patched_files(self):
        execute(self.root, PATCH, self.sha)
        original = files_snapshot(self.root)
        applied, previously = execute(self.root, PATCH, self.sha)
        self.assertEqual((applied, previously), (0, 3))
        self.assertEqual(original, files_snapshot(self.root))

    def test_partial_install_repairs_only_missing_file(self):
        apply_one(self.root, 0, self.scratch)
        apply_one(self.root, 1, self.scratch)
        before = files_snapshot(self.root)
        applied, previously = execute(self.root, PATCH, self.sha)
        after = files_snapshot(self.root)
        self.assertEqual((applied, previously), (1, 2))
        for part in load_sections(PATCH)[:2]:
            self.assertEqual(before[part.path], after[part.path])
        self.assertNotEqual(before["svc/pipeline.py"], after["svc/pipeline.py"])

    def test_preflight_conflict_prevents_any_patch_mutation(self):
        p = self.root / "svc" / "pipeline.py"
        content = p.read_bytes()
        self.assertIn(b"weights_only=False", content)
        p.write_bytes(content.replace(b"weights_only=False", b"weights_only=None"))
        original = files_snapshot(self.root)
        with self.assertRaisesRegex(RuntimeError, "svc/pipeline.py"):
            execute(self.root, PATCH, self.sha)
        self.assertEqual(original, files_snapshot(self.root))

    def test_patched_then_foreign_change_is_rejected_if_hunk_conflicts(self):
        execute(self.root, PATCH, self.sha)
        p = self.root / "svc" / "pipeline.py"
        content = p.read_bytes()
        self.assertIn(b"weights_only=True", content)
        p.write_bytes(content.replace(b"weights_only=True", b"weights_only=maybe"))
        before = files_snapshot(self.root)
        with self.assertRaisesRegex(RuntimeError, "svc/pipeline.py"):
            execute(self.root, PATCH, self.sha)
        self.assertEqual(before, files_snapshot(self.root))

    def test_windows_crlf_working_tree(self):
        # Some Windows Git installations check out Python files with CRLF.
        for part in load_sections(PATCH):
            path = self.root / part.path
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        applied, previously = execute(self.root, PATCH, self.sha)
        self.assertEqual((applied, previously), (3, 0))
        for part in load_sections(PATCH):
            content = (self.root / part.path).read_bytes()
            self.assertEqual(content.count(b"\n"), content.count(b"\r\n"))
        self.assertEqual(execute(self.root, PATCH, self.sha), (0, 3))

    def test_partial_crlf_install_recovers_untouched_targets(self):
        for part in load_sections(PATCH):
            target = self.root / part.path
            target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
        first = load_sections(PATCH)[0]
        isolated = self.scratch / "first-crlf.patch"
        isolated.write_bytes(first.data.replace(b"\n", b"\r\n"))
        git(self.root, "apply", str(isolated))
        before = (self.root / first.path).read_bytes()
        applied, already = execute(self.root, PATCH, self.sha)
        self.assertEqual((applied, already), (2, 1))
        self.assertEqual((self.root / first.path).read_bytes(), before)

    def test_mixed_line_endings_are_not_rewritten(self):
        part = load_sections(PATCH)[-1]
        target = self.root / part.path
        content = target.read_bytes()
        target.write_bytes(content.replace(b"\n", b"\r\n", 4))
        before = files_snapshot(self.root)
        with self.assertRaisesRegex(RuntimeError, "mixed LF and CRLF"):
            execute(self.root, PATCH, self.sha)
        self.assertEqual(files_snapshot(self.root), before)

    def test_wrong_git_pin_is_never_modified(self):
        before = files_snapshot(self.root)
        with self.assertRaisesRegex(RuntimeError, "Wrong ApexSVC Git commit"):
            execute(self.root, PATCH, "0"*40)
        self.assertEqual(before, files_snapshot(self.root))


if __name__ == "__main__":
    unittest.main(verbosity=2)

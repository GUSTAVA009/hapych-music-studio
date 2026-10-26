#!/usr/bin/env python3
"""Safe upgrade tests for Seed-VC overlay: no AI models, no user recordings."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from install_seed_overlays import run, MANIFEST, BACKUPS

class TestSeedOverlayInstaller(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="hapych-seed-overlays-")
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.repo=base/"seed from upstream"
        self.source=base/"hapych overlay"
        self.repo.mkdir()
        self.source.mkdir()
        def git(*args):
            p=subprocess.run(["git","-C",str(self.repo),*args],capture_output=True,text=True)
            if p.returncode:
                raise AssertionError(p.stderr)
            return p.stdout.strip()
        self.git=git
        git("init","-q")
        git("config","user.name","HAPYCH CI")
        git("config","user.email","ci@example.invalid")
        (self.repo/"README.md").write_text("Genuine Seed-VC upstream\n",encoding="utf-8")
        git("add","README.md")
        git("commit","-qm","Synthetic safe upstream")
        self.pin=git("rev-parse","HEAD")
        self.script=self.source/"inference_studio75.py"
        self.script.write_text("VERSION = 1\n",encoding="utf-8")

    def test_first_install_and_second_install_are_safe(self):
        self.assertEqual(run(self.repo,self.source,self.pin)["new"],1)
        before=(self.repo/"inference_studio75.py").read_bytes()
        self.assertEqual(run(self.repo,self.source,self.pin)["skip"],1)
        self.assertEqual((self.repo/"inference_studio75.py").read_bytes(),before)
        self.assertTrue((self.repo/MANIFEST).is_file())

    def test_changed_official_overlay_migrates_and_creates_a_backup(self):
        run(self.repo,self.source,self.pin)
        self.script.write_text("VERSION = 2\n",encoding="utf-8")
        result=run(self.repo,self.source,self.pin)
        self.assertEqual(result["upgrade"],1)
        self.assertEqual((self.repo/"inference_studio75.py").read_text(), "VERSION = 2\n")
        backup=list((self.repo/BACKUPS).rglob("inference_studio75.py"))
        self.assertEqual(len(backup),1)
        self.assertEqual(backup[0].read_text(), "VERSION = 1\n")

    def test_existing_untracked_legacy_overlay_is_backed_up_not_deleted(self):
        (self.repo/"inference_studio75.py").write_text("LEGACY = 100\n",encoding="utf-8")
        result=run(self.repo,self.source,self.pin)
        self.assertEqual(result["legacy_upgrade"],1)
        backup=list((self.repo/BACKUPS).rglob("inference_studio75.py"))
        self.assertEqual(len(backup),1)
        self.assertEqual(backup[0].read_text(),"LEGACY = 100\n")
        self.assertEqual((self.repo/"inference_studio75.py").read_text(),"VERSION = 1\n")

    def test_user_changes_are_never_overwritten(self):
        run(self.repo,self.source,self.pin)
        target=self.repo/"inference_studio75.py"
        target.write_text("MY_PERSONAL_PATCH = True\n",encoding="utf-8")
        self.script.write_text("VERSION = 2\n",encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"local/user modifications"):
            run(self.repo,self.source,self.pin)
        self.assertEqual(target.read_text(),"MY_PERSONAL_PATCH = True\n")

    def test_upstream_git_tracked_file_is_never_overwritten(self):
        (self.repo/"inference_studio75.py").write_text("UPSTREAM_SOURCE = 1\n",encoding="utf-8")
        self.git("add","inference_studio75.py")
        self.git("commit","-qm","Add upstream file")
        next_pin=self.git("rev-parse","HEAD")
        with self.assertRaisesRegex(RuntimeError,"upstream tracked file"):
            run(self.repo,self.source,next_pin)
        self.assertEqual((self.repo/"inference_studio75.py").read_text(),"UPSTREAM_SOURCE = 1\n")

    def test_wrong_git_commit_must_refuse(self):
        with self.assertRaisesRegex(RuntimeError,"pinned Git commit"):
            run(self.repo,self.source,"0"*40)
        self.assertFalse((self.repo/"inference_studio75.py").exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)

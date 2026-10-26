#!/usr/bin/env python3
"""Windows installer regression tests that do not download model weights."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent

class TestVoiceWindowsInstaller(unittest.TestCase):

    def setUp(self):
        self.requirements = (ROOT/"requirements/voice-engine-win-lock.txt").read_text(encoding="utf-8")
        self.installer = (ROOT/"scripts/Install-Windows.ps1").read_text(encoding="utf-8-sig")
        self.workflow = (ROOT/".github/workflows/source_audit.yml").read_text(encoding="utf-8")

    def test_no_source_only_webrtcvad_or_resemblyzer_in_main_dependency_lock(self):
        requirements = [x.strip().lower() for x in self.requirements.splitlines()
                        if x.strip() and not x.strip().startswith("#")]
        names = {re.split(r"(?=[<>=!~\[])", x, maxsplit=1)[0].strip() for x in requirements}
        self.assertNotIn("webrtcvad", names)
        self.assertNotIn("resemblyzer", names)
        self.assertIn("webrtcvad-wheels", names)
        self.assertIn("torch", names)
        self.assertIn("torchaudio", names)

    def test_resemblyzer_explicit_binary_install_without_obsolete_build(self):
        self.assertIn("--no-deps --only-binary :all: 'resemblyzer==0.1.4'", self.installer)
        self.assertIn("tools\\verify_voice_runtime.py", self.installer)
        self.assertNotIn("uv pip install --python $voicePython --extra-index-url", self.installer)

    def test_main_packages_stay_on_pypi_and_cuda_on_pytorch_index(self):
        self.assertIn("--default-index 'https://pypi.org/simple'", self.installer)
        self.assertIn("--torch-backend cu121", self.installer)
        self.assertNotIn("--index-strategy unsafe-best-match", self.installer)

    def test_existing_ace_and_apex_venvs_do_not_prune_studio_extras(self):
        self.assertIn("uv sync --project $ace --frozen --inexact --python 3.11", self.installer)
        self.assertIn("uv sync --project $apex --frozen --inexact --python 3.10", self.installer)

    def test_installer_checks_running_music_service_before_mutating_env(self):
        self.assertIn("foreach($port in @(7870,7862))", self.installer)
        self.assertIn("Close Music Studio and its ACE-Step processes before updating", self.installer)

    def test_ci_has_clean_windows_package_and_no_compilation_checks(self):
        self.assertIn("dry-run", self.workflow)
        self.assertIn("test_voice_win_install.py", self.workflow)
        self.assertIn("webrtcvad-wheels==2.0.14.post1", self.workflow)
        self.assertIn("resemblyzer==0.1.4", self.workflow)

if __name__=="__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Portable regression: public Music Studio must generate without private Groove23.

No AI models, licensed samples, GPU or user songs are needed. We fake the
remote ACE-Step client to ensure the optional feature cannot block the real
music-generation routing, and that no trained weights are claimed unless used.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP))

# CI runs without heavy Music Studio third-party dependencies. Substitute
# harmless stubs only in this short-lived test process.
client_stub = types.ModuleType("gradio_client")
arrangement_stub = types.ModuleType("arrangement25")
audio_guard_stub = types.ModuleType("audio_guard55")
client_stub.Client = object
client_stub.handle_file = lambda path: "local-file:" + str(path)
arrangement_stub.make_reference = lambda *args: (_ for _ in ()).throw(
    AssertionError("Reference builder must not run for missing training assets")
)
audio_guard_stub.inspect_source = lambda path: {"status": "fixture-pass"}
sys.modules["gradio_client"] = client_stub
sys.modules["arrangement25"] = arrangement_stub
sys.modules["audio_guard55"] = audio_guard_stub

import groove_preflight
import composer90


class FakeTask:
    def __init__(self, output: Path):
        self.output = output

    def done(self):
        return True

    def result(self):
        return [str(self.output)]


class FakeClient:
    output = None
    calls: list = []

    def __init__(self, *args, **kwargs):
        pass

    def predict(self, *args, **kwargs):
        return None

    def submit(self, *args, **kwargs):
        self.calls.append(args)
        return FakeTask(self.output)


def fake_config():
    inputs = [
        {"id": index, "type": "textbox", "props": {"label": "control_%d" % index}}
        for index in range(72)
    ]
    inputs.append({"id": 72, "type": "audio",
                   "props": {"label": "🎵 Generated Music (Sample 1)"}})
    return {"components": inputs,
            "dependencies": [{"api_name": "generation_wrapper",
                              "inputs": list(range(72)), "outputs": [72]}]}


def fake_groove_assets(root: Path):
    assets = {
        "Training Runs/groove23/best_groove_model.pt": b"fake-checkpoint-for-preflight",
        "Training Runs/groove23/groove_model23.py": b"# fake model\n",
        "Sound Library/catalog20.json": b'{"samples":[]}',
        "Sound Library/packs/test.wav": b"mock",
        "ACE-Step-1.5/.venv/Scripts/python.exe": b"mock",
    }
    for relative, data in assets.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)


class TestPublicInstallWithoutPrivateGroove(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hapych-no-private-groove-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "fixture.wav"
        self.output.write_bytes(b"mock-audio-for-testing-no-real-generation")
        FakeClient.output = self.output
        FakeClient.calls = []
        self.stage = []
        self.original_root = composer90.ROOT
        self.original_seed = composer90.fresh_seeds
        composer90.ROOT = self.root
        composer90.fresh_seeds = lambda style, count: list(range(1234,1234+count))
        self.addCleanup(setattr, composer90, "ROOT", self.original_root)
        self.addCleanup(setattr, composer90, "fresh_seeds", self.original_seed)

    def compose(self, opt: bool, mode: str = "new"):
        settings = {
            "Batch Size": 1,
            "Music Caption": "Trap, 808 kick",
            "__style_plan": {"reference_policy": "trained_808"},
            "__use_trained_groove_reference": opt,
            "BPM (Beats Per Minute)": 120,
            "Key": "",
        }
        return composer90.compose(settings, fake_config(), "trap 808",
                                  mode, "http://127.0.0.1:7862",
                                  "TEST-NO-MODELS", self.stage.append,
                                  client_factory=FakeClient)

    def test_public_source_install_marks_optional_assets_unavailable(self):
        status = groove_preflight.availability(self.root)
        self.assertFalse(status["available"])
        self.assertTrue(status["optional"])
        self.assertIn("groove23 checkpoint", status["missing"])
        self.assertIn("licensed sample catalog", status["missing"])
        with self.assertRaises(groove_preflight.GrooveReferenceUnavailable):
            groove_preflight.ensure_available(self.root)

    def test_music_generation_continues_when_private_groove_is_missing(self):
        paths, timestamps, records = self.compose(opt=True)
        self.assertEqual(paths, [str(self.output)])
        self.assertEqual(len(FakeClient.calls), 1)
        self.assertIsNone(records[0]["reference"])
        self.assertEqual(records[0]["reference_source"], "optional_groove_unavailable")
        self.assertFalse(records[0]["automatic_minor_key_forced"])
        self.assertIn("groove23", records[0]["groove_reference_warning"])
        self.assertTrue(any("groove23" in message for message in self.stage))

    def test_opt_out_does_not_touch_private_groove(self):
        paths, _, records = self.compose(opt=False)
        self.assertEqual(paths, [str(self.output)])
        self.assertIsNone(records[0]["groove_reference_warning"])
        self.assertEqual(records[0]["reference_source"], "none")

    def test_available_files_report_available(self):
        fake_groove_assets(self.root)
        status = groove_preflight.availability(self.root)
        self.assertTrue(status["available"])
        self.assertFalse(status["missing"])

    def test_reference_renderer_failure_never_aborts_main_generation(self):
        fake_groove_assets(self.root)
        with mock.patch.object(composer90, "make_reference",
                               side_effect=FileNotFoundError("one sample missing")):
            paths, _, records = self.compose(opt=True)
        self.assertEqual(paths, [str(self.output)])
        self.assertIn("FileNotFoundError", records[0]["groove_reference_warning"])
        self.assertIsNone(records[0]["reference"])
        self.assertFalse(records[0]["automatic_minor_key_forced"])

    def test_trained_reference_is_used_only_if_available_and_explicit(self):
        fake_groove_assets(self.root)
        mock_reference = {
            "path": str(self.output),
            "kind": "trained_groove24_sample_reference",
            "reference_key": "A minor",
            "bpm": 120,
            "plan": {"chords": [{"name": "Am"}]},
            "learned_weights_used": True,
        }
        with mock.patch.object(composer90, "make_reference", return_value=mock_reference) as call:
            paths, _, records = self.compose(opt=True)
            self.assertEqual(call.call_count, 1)
        self.assertEqual(paths, [str(self.output)])
        self.assertEqual(records[0]["reference_source"], "explicit_groove_opt_in")
        self.assertIsNone(records[0]["groove_reference_warning"])
        self.assertTrue(records[0]["automatic_minor_key_forced"])

    def test_remix_never_loads_experimental_groove(self):
        paths, _, records = self.compose(opt=True, mode="remix")
        self.assertEqual(paths, [str(self.output)])
        self.assertIsNone(records[0]["groove_reference_warning"])

if __name__ == "__main__":
    unittest.main(verbosity=2)

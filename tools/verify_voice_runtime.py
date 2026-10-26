#!/usr/bin/env python3
"""Verify actual Windows Voice Engine imports, including native DLL libraries.

No models are loaded, no generated songs or microphone recordings are read.
The Resemblyzer compatibility shim uses webrtcvad-wheels (a prebuilt wheel
that provides the webrtcvad module), not the old source-only webrtcvad.
"""
from __future__ import annotations
from importlib import metadata
import json
import sys

def main() -> int:
    issues: list[str] = []
    versions: dict[str, str] = {}
    for name in ("torch", "torchaudio", "torchvision", "numpy", "librosa",
                 "soundfile", "resemblyzer", "webrtcvad-wheels", "huggingface-hub"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            issues.append(f"Missing package: {name}")

    if issues:
        print(json.dumps({"ok": False, "errors": issues}, ensure_ascii=False))
        return 1

    try:
        from resemblyzer import VoiceEncoder
        import webrtcvad
        import torch
        import torchaudio
        import librosa
        import soundfile
        from huggingface_hub import hf_hub_download

        if not hasattr(VoiceEncoder, "embed_utterance"):
            issues.append("Resemblyzer VoiceEncoder method missing")
        if not isinstance(webrtcvad.Vad(1).is_speech(bytes(320), 16000), bool):
            issues.append("Prebuilt WebRTC VAD C extension does not function")
        if torch.__version__.split("+", 1)[0] != torchaudio.__version__.split("+", 1)[0]:
            issues.append("torch and torchaudio ABI versions differ")
        if not hasattr(librosa, "load") or not hasattr(soundfile, "read"):
            issues.append("Audio file decoders could not initialize")
        if not callable(hf_hub_download):
            issues.append("Hugging Face model downloader unavailable")
    except Exception as exc:
        issues.append(f"Voice Engine runtime import failed: {type(exc).__name__}: {exc}")

    print(json.dumps({"ok": not issues,
                      "versions": versions,
                      "errors": issues,
                      "note": "Model inference and actual singing have not been tested."},
                     ensure_ascii=False))
    return 0 if not issues else 1

if __name__ == "__main__":
    sys.exit(main())

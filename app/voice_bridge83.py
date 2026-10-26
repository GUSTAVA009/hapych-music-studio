"""Bridge Music Studio with locally installed Demucs + Seed-VC.
Creates a NEW track; the original audio and voice recordings stay unchanged.
"""
import os
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE_ENGINE = ROOT / "Voice Engine"
PYTHON = VOICE_ENGINE / ".venv" / "Scripts" / "python.exe"
PIPELINE = VOICE_ENGINE / "convert_track_studio83.py"
BRIDGE_LOG = VOICE_ENGINE / "voice-bridge83.log"

def convert_song(source, reference, output, on_stage=None, steps=40, trained=False, pitch_smooth=0.0, register_mode="original", vocal_language="unknown", chorus_ranges=None):
    source, reference, output = map(Path, (source, reference, output))
    if not source.is_file() or not reference.is_file():
        raise RuntimeError("Не найден исходный трек или запись голоса.")
    if not PYTHON.is_file() or not PIPELINE.is_file():
        raise RuntimeError("Голосовой движок QA83 Seed-VC не установлен.")
    if source.resolve() == output.resolve():
        raise RuntimeError("Для безопасности нельзя перезаписывать исходную песню.")
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    environment = os.environ.copy()
    environment.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                       HF_HUB_DISABLE_XET="1", NO_PROXY="127.0.0.1,localhost,::1",
                       no_proxy="127.0.0.1,localhost,::1")
    command = [str(PYTHON), "-u", str(PIPELINE), "--source", str(source),
               "--voice", str(reference), "--output", str(output),
               "--steps", str(steps), "--register", register_mode, "--language", vocal_language,
               "--chorus-ranges", json.dumps(chorus_ranges or [])]
    if trained:
        command.append("--trained")
    if on_stage:
        on_stage("Запускаем перенос голоса — отделяем вокал...")
    recent = []
    rejected = ""
    with BRIDGE_LOG.open("a", encoding="utf-8", errors="replace") as log:
        log.write("\nSTART " + source.name + " -> " + output.name + "\n")
        log.flush()
        process = subprocess.Popen(command, cwd=str(VOICE_ENGINE),
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                   errors="replace", env=environment,
                                   creationflags=flags, bufsize=1)
        try:
            for line in process.stdout:
                line = line.strip()
                if line:
                    log.write(line + "\n")
                    log.flush()
                    recent.append(line)
                    recent = recent[-12:]
                if line.startswith("VOICE_REJECTED:"): rejected = line.split(":",1)[1]
                if line.startswith("STAGE:") and on_stage:
                    on_stage(line[len("STAGE:"):].strip())
            result = process.wait(timeout=1800)
        except BaseException:
            process.kill()
            process.wait()
            raise
    if result != 0 or not output.is_file() or output.stat().st_size < 10000:
        output.unlink(missing_ok=True)
        if rejected: raise RuntimeError(rejected)
        raise RuntimeError("Не удалось перенести тембр. См. Voice Engine/voice-bridge.log. "
                           + " ".join(recent[-2:])[:300])
    return output

"""Single local, resource-guarded voice fine-tuning process for Music Studio.
Saves independent checkpoints; never overwrites pretrained Seed-VC weights.
"""
import os
import re
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "Voice Engine" / "seed-vc"
PYTHON = ROOT / "Voice Engine" / ".venv" / "Scripts" / "python.exe"
TRAIN_SCRIPT = SEED / "train_hapych_lowvram.py"
TRAIN_DATA = ROOT / "Voice Engine" / "training_dataset" / "ALEX_KZNT_SHORT"
RUN_DIR = SEED / "runs" / "music_studio_personal_v1"
LOG = ROOT / "Voice Engine" / "voice-training-active.log"
STEPS = 100

_lock = threading.RLock()
_process = None
_returncode = None

def status():
    global _returncode
    with _lock:
        proc = _process
        if proc is not None:
            polled = proc.poll()
            if polled is not None:
                _returncode = polled
        else:
            polled = None
        checkpoint = RUN_DIR / "ft_model.pth"
        ready = checkpoint.is_file() and checkpoint.stat().st_size > 10000000
        raw = LOG.read_bytes() if LOG.exists() else b""
        lines = raw.decode("utf-8", errors="replace")
        matches = re.findall(r"epoch\s+\d+,\s+step\s+(\d+),\s+loss:\s+([\d.]+)", lines)
        progress = int(matches[-1][0]) if matches else 0
        active = proc is not None and polled is None
        return {
            "active": active, "ready": ready,
            "step": progress, "total": STEPS,
            "exit_code": _returncode,
            "samples": len(list(TRAIN_DATA.glob("*.wav"))) if TRAIN_DATA.exists() else 0,
            "message": "Идёт донастройка на видеокарте" if active else
                       "Обученная модель сохранена; нужна проверка звучания" if ready else
                       "Обучение завершилось с ошибкой; смотри журнал" if _returncode not in (None, 0) else
                       "Готово к обучению",
            "log_tail": lines[-1300:],
        }

def launch():
    global _process, _returncode
    with _lock:
        current = status()
        if current["active"]:
            raise RuntimeError("Обучение голоса уже запущено.")
        if current["samples"] < 4:
            raise RuntimeError("Нужно минимум четыре коротких образца голоса.")
        if not PYTHON.is_file() or not TRAIN_SCRIPT.is_file():
            raise RuntimeError("Не найдены файлы обучающей программы.")
        if current["ready"]:
            raise RuntimeError("Модель уже обучена; повторная тренировка требует отдельной версии.")
        environment = os.environ.copy()
        environment.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
            HF_HUB_DISABLE_XET="1", NO_PROXY="127.0.0.1,localhost,::1",
            no_proxy="127.0.0.1,localhost,::1",
            HTTP_PROXY="", HTTPS_PROXY="", ALL_PROXY="")
        command = [str(PYTHON), "-u", str(TRAIN_SCRIPT),
                   "--config", "configs/presets/config_dit_mel_seed_uvit_whisper_base_f0_44k.yml",
                   "--dataset-dir", str(TRAIN_DATA),
                   "--run-name", "music_studio_personal_v1",
                   "--batch-size", "1", "--max-steps", str(STEPS),
                   "--max-epochs", "300", "--save-every", "10",
                   "--num-workers", "0"]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("w", encoding="utf-8") as log:
            _process = subprocess.Popen(command, cwd=str(SEED),
                stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=flags, env=environment)
        _returncode = None
        return status()

def stop():
    with _lock:
        st = status()
        if not st["active"]:
            return st
        process = _process
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True, text=True, timeout=15)
        else:
            process.terminate()
        return status()

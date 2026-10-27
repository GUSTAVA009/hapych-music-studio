# Music Studio - Russian local production interface
# Local-only HTTP service. ACE-Step is a separate localhost generation engine.
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse, quote

_localhost_proxy_exclusion = "127.0.0.1,localhost,::1"
for _proxy_key in ("NO_PROXY", "no_proxy"):
    _present = os.environ.get(_proxy_key, "")
    os.environ[_proxy_key] = ",".join(x for x in (_present, _localhost_proxy_exclusion) if x)
# Do not destroy HTTP[S]_PROXY or ALL_PROXY: official ACE-Step checkpoints
# may require the user's proxy to download on a different computer.

import requests
from gradio_client import Client, handle_file
from arrangement25 import make_reference, needs_808
from groove_preflight import availability as groove_availability
from composer90 import compose as compose_independent
from sound_effects29 import planned_effects, render_effects
from voice_bridge83 import convert_song
from voice_model_policy63 import select as select_voice_model
from studio_finisher34 import finish as finish_master34
from chorus_layers34 import chorus_windows
import voice_profiles34
from studio_titles17 import resolve_title
from studio_sections import prepare_request as prepare_sections
from music_plan17 import key_from_brief
from prompt_integrity85 import compile_brief
from duration42 import resolve_duration
from track_details26 import get_details
from cover_art35 import ensure_cover, cover_path
from studio_storage40 import storage_paths, open_storage_folder
from cover_pipeline40 import queue_cover, cover_info, regenerate_cover, generated_cover_path

def prepare_request(data):
    result = prepare_sections(data)
    compiled = compile_brief(data.get("style", ""), result)
    result["caption"] = compiled["caption"]
    result["caption_length"] = len(result["caption"])
    result["style_plan"] = compiled["style_plan"]
    result["time_signature"] = compiled["time_signature"]
    result["warnings"].extend(compiled["warnings"])
    result["sample_reference_requested"] = compiled["style_plan"]["reference_policy"] == "trained_808"
    result["groove_reference"] = groove_availability(Path(__file__).resolve().parent.parent)
    if (bool(data.get("use_trained_groove_reference")) and result["sample_reference_requested"]
            and not result["groove_reference"]["available"]):
        result["warnings"].append(result["groove_reference"]["message"])
    result["music_key"] = key_from_brief(data.get("style", ""))
    # SFX listed only in the style field must not disappear in caption packing.
    # Route them into post-production, without duplicating cues from the lyrics.
    style_sfx = compiled["style_plan"].get("sound_effects_in_style", [])
    if style_sfx:
        from sound_effects29 import canonical as sound_name
        sections = result.setdefault("sections", [])
        if not sections:
            sections.append({"id":"section_01","section":"Intro","index":0,
                             "instructions":[],"lyrics":"","model_tag":"[Instrumental]"})
        effects_before = planned_effects(sections)
        known = set(e["effect"] for e in effects_before)
        extras = []
        for raw in style_sfx:
            key = sound_name(raw)
            if key and key in known:continue
            sections[0].setdefault("instructions", []).append({"text":"SFX: "+raw,"line":0})
            extras.append(raw)
            if key:known.add(key)
        result["style_sfx_added"]=extras
        result["effects_plan"]=planned_effects(sections)
        if extras:result["warnings"].append("SFX из поля стиля отправлены в постобработку, а не потеряны при сокращении промпта: "+", ".join(extras))
    # Musical transition guidance is separate from the non-destructive final fade.
    from song_structure34 import condition as arrange_edges
    wanted_seconds,_ = resolve_duration(data.get("duration",0),data.get("style",""))
    result["lyrics"],structure=arrange_edges(result["lyrics"],data.get("style",""),wanted_seconds,bool(data.get("instrumental")))
    result["structure_plan"]=structure
    result["lyrics_length"]=len(result["lyrics"])
    result["warnings"].extend(structure.get("notes",[]))
    return result
import studio_workflow as workflow
import voice_training
import training_reservation23
import training41_guard
import training32_guard

APP = Path(__file__).resolve().parent
ROOT = APP.parent
ENGINE = ROOT / "ACE-Step-1.5"
VOICES = ROOT / "Мой голос"
TRACKS = ROOT / "Мои треки"
ORIGINALS = ROOT / "Исходные версии"
MASTERS = ROOT / "Мастер WAV"
INPUTS = ROOT / "Входное аудио"
BEAT_SAMPLES = ROOT / "Обучение" / "Примеры битов"
VOICE_TRAINING = ROOT / "Voice Engine" / "seed-vc" / "runs" / os.environ.get("MUSIC_STUDIO_TRAINING_RUN", "music_studio_personal_v1")
VOICE_TRAIN_LOG = ROOT / "Voice Engine" / "voice-training.log"
NORMALIZED = APP / "audio_cache"
RUSSIAN_RAP_MODEL = APP / "models" / "russian-rap" / "final"
UI = APP / "ui"
LOG = ROOT / "Music Studio.log"
WEBLOG = APP / "studio-server.log"
BATCH = ROOT / "Music Studio Composer.bat"
ENGINE_URL = "http://127.0.0.1:7862"
SFT_URL = "http://127.0.0.1:7861"
COMPOSER_URL = "http://127.0.0.1:7862"
COMPOSER_BATCH = ROOT / "Music Studio Composer.bat"
SFT_BATCH = ROOT / "Music Studio SFT HQ.bat"
PORT = int(os.environ.get("MUSIC_STUDIO_PORT", "7870"))
MAX_UPLOAD = 90 * 1024 * 1024

for directory in (VOICES, TRACKS, ORIGINALS, MASTERS, INPUTS, BEAT_SAMPLES, NORMALIZED, UI):
    directory.mkdir(parents=True, exist_ok=True)

lock = threading.RLock()
state = {"id": None, "status": "idle", "message": "Готово к работе", "files": [], "error": "", "started": None}
http = requests.Session()
http.trust_env = False

def engine_ok(url=ENGINE_URL):
    try:
        r = http.get(url + "/config", timeout=2.5)
        return r.status_code == 200 and "dependencies" in r.json()
    except Exception:
        return False

# Separate startup state from the HTTP server: the browser must remain
# responsive even if model initialization crashes or takes many minutes.
_engine_start_lock = threading.Lock()
_engine_process = None
_engine_start_error = ""
_engine_started_at = None

def engine_snapshot(connected=None):
    connected = engine_ok() if connected is None else bool(connected)
    if connected:
        status, detail = "connected", "ACE-Step отвечает на локальном порту 7862"
    elif _engine_start_error:
        status, detail = "error", _engine_start_error
    elif _engine_process is not None:
        exit_code = _engine_process.poll()
        if exit_code is not None:
            status, detail = "error", ("ACE-Step завершился с кодом %s. "
                       "Проверь журнал Music Studio.log и запусти scripts/Diagnose-Windows.ps1." % exit_code)
        else:
            status, detail = "starting", "ACE-Step загружается или инициализирует модели"
    elif not (ENGINE / ".venv" / "Scripts" / "acestep.exe").is_file():
        status, detail = "missing", "ACE-Step не установлен: запусти Install-Windows.ps1"
    else:
        status, detail = "not_started", "ACE-Step ещё не запускался"
    return {"status": status, "message": detail,
            "process_alive": bool(_engine_process is not None and _engine_process.poll() is None),
            "engine_executable_present": (ENGINE / ".venv" / "Scripts" / "acestep.exe").is_file()}

def start_engine():
    global _engine_process, _engine_start_error, _engine_started_at
    # Do not create duplicate ACE-Step processes while the first one is
    # downloading/initializing. Gradio /config is not immediate on first launch.
    if engine_ok():
        return
    if _engine_process is not None:
        exit_code = _engine_process.poll()
        if exit_code is None:
            return
        _engine_start_error = ("ACE-Step завершился при запуске (код %s). "
                             "Запусти scripts/Diagnose-Windows.ps1 и проверь Music Studio.log." % exit_code)
        raise RuntimeError(_engine_start_error)
    executable = ENGINE / ".venv" / "Scripts" / "acestep.exe"
    if not executable.is_file():
        _engine_start_error = ("Не найден ACE-Step. Запусти "
                               "scripts/Install-Windows.ps1 и scripts/Diagnose-Windows.ps1.")
        raise RuntimeError(_engine_start_error)
    # Let ACE-Step auto-detect GPU/CPU, VRAM, LLM size, quantization and
    # offloading. Previous hard-coded RTX/CUDA and 1.7B LLM broke other PCs.
    # Keep PyTorch LM backend for broad Windows GPU compatibility.
    arguments = [
        str(executable), "--port", "7862", "--server-name", "127.0.0.1",
        "--language", "en", "--config_path", "acestep-v15-turbo",
        "--backend", "pt", "--init_service", "true", "--batch_size", "1",
    ]
    environment = os.environ.copy()
    environment.update(PYTHONUTF8="1", CHECK_UPDATE="false")
    try:
        with LOG.open("a", encoding="utf-8", errors="replace") as stream:
            stream.write("\n===== ACE-STEP AUTO DEVICE / AUTO LLM / PORT 7862 =====\n")
            stream.flush()
            process = subprocess.Popen(arguments, cwd=str(ENGINE),
                         stdin=subprocess.DEVNULL, stdout=stream,
                         stderr=subprocess.STDOUT, env=environment,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        _engine_process = process
        _engine_started_at = datetime.now().isoformat()
        _engine_start_error = ""
    except Exception as exc:
        _engine_start_error = ("ACE-Step не удалось запустить (%s). "
                             "Запусти scripts/Diagnose-Windows.ps1." % type(exc).__name__)
        raise

def _background_start_engine():
    global _engine_start_error
    with _engine_start_lock:
        try:
            start_engine()
        except Exception:
            with WEBLOG.open("a", encoding="utf-8") as log:
                traceback.print_exc(file=log)

def ensure_unified_engine():
    global _engine_start_error
    if engine_ok():
        return
    with _engine_start_lock:
        if engine_ok():
            return
        start_engine()
        # First-run model downloads can be much longer than the old 180 sec.
        max_wait = max(90, min(3600, int(os.environ.get("MUSIC_STUDIO_ENGINE_WAIT_SECONDS", "1200"))))
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            if engine_ok():
                return
            if _engine_process is not None:
                exit_code = _engine_process.poll()
                if exit_code is not None:
                    _engine_start_error = ("ACE-Step завершился с кодом %s при инициализации. "
                      "Проверь Music Studio.log и запусти scripts/Diagnose-Windows.ps1." % exit_code)
                    raise RuntimeError(_engine_start_error)
            time.sleep(2)
        raise RuntimeError("ACE-Step не ответил за %s секунд. Возможно, модели скачиваются "
            "или видеокарте не хватает памяти. Запусти scripts/Diagnose-Windows.ps1." % max_wait)

def copy_job():
    with lock:
        return dict(state, files=[dict(f) for f in state["files"]])

def update_job(**kw):
    with lock:
        state.update(kw)

def safe_name(s, default="audio"):
    s = Path(str(s).replace("\\", "/")).name
    s = re.sub(r"[^\w.\- ]+", "", s, flags=re.UNICODE).strip().replace(" ", "_")
    return s[:100] or default

def basename_in(directory, name):
    raw = unquote(name)
    base = Path(raw.replace("\\", "/")).name
    if raw != base or not base:
        return None
    p = (directory / base).resolve()
    if p.parent != directory.resolve():
        return None
    return p

def media_list(directory):
    allowed = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}
    rows = []
    for path in sorted(directory.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if path.is_file() and path.suffix.lower() in allowed:
            # Older generations saved both baseline and VC files in the same
            # library. Only show the final voice version if a pair exists.
            if directory == TRACKS and not path.stem.endswith("_МОЙ_ГОЛОС"):
                if (directory / (path.stem + "_МОЙ_ГОЛОС" + path.suffix)).is_file():
                    continue
            row = {"name": path.name, "mtime": path.stat().st_mtime, "size": path.stat().st_size,
                   "when": datetime.fromtimestamp(path.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
                   "url": ("/api/audio/" if directory == TRACKS else "/api/voice/") + path.name}
            if directory == TRACKS and path.stem.endswith("_МОЙ_ГОЛОС"):
                baseline = path.stem[:-len("_МОЙ_ГОЛОС")] + path.suffix
                if (ORIGINALS / baseline).is_file():
                    row["original_url"] = "/api/original/" + baseline
                    row["original_name"] = baseline
                elif (TRACKS / baseline).is_file():
                    row["original_url"] = "/api/audio/" + baseline
                    row["original_name"] = baseline
            if directory == TRACKS:
                if path.suffix.lower() == ".mp3":
                    row["cover_url"] = "/api/cover/" + quote(path.name)
                master_name = path.with_suffix(".wav").name
                if (MASTERS / master_name).is_file(): row["master_url"] = "/api/master/" + master_name
                if path.stem.endswith("_МОЙ_ГОЛОС") and "original_url" not in row:
                    for ext in (".wav", ".flac"):
                        baseline = path.stem[:-len("_МОЙ_ГОЛОС")] + ext
                        if (ORIGINALS / baseline).is_file():
                            row.update(original_url="/api/original/" + baseline, original_name=baseline)
                            break
            metadata = path.with_suffix(".track.json")
            if directory == TRACKS and metadata.is_file():
                try:
                    saved = json.loads(metadata.read_text(encoding="utf-8"))
                    for key in ("learned_rhythm", "rhythm_model_step", "voice_check_status", "voice_check_note", "title", "title_origin", "variant", "voice_applied", "master_url", "original_url", "original_name", "fx_url", "effects", "production_warnings", "sample_guided_808", "acoustic_quality_verified"):
                        if key in saved: row[key] = saved[key]
                    # The list uses the saved original style, never invented tags.
                    summary = str(saved.get("style_original") or saved.get("model_caption")
                                  or saved.get("caption_sent") or "").replace("\n", " ").strip()
                    if summary: row["style_preview"] = summary[:220]
                    row["cover_generation"] = cover_info(path)["status"]
                except (OSError, ValueError): pass
            if directory == VOICES:
                artist_id=voice_profiles34.assignment(path.name).get("profile_id")
                row["profile_id"]=artist_id or ""
                if artist_id:
                    known={a["id"]:a["name"] for a in voice_profiles34.list_profiles()["profiles"]}
                    row["artist_name"]=known.get(artist_id,"")
            if directory == VOICES and path.suffix.lower() == ".wav":
                sidecar=path.with_name(path.name+".json")
                if sidecar.is_file():
                    try:
                        recording=json.loads(sidecar.read_text(encoding="utf-8"))
                        row["recording_warning"]=str(recording.get("warning",""))[:260]
                        row["recording_peak_dbfs"]=recording.get("peak_dbfs")
                        row["recording_seconds"]=recording.get("seconds")
                    except (OSError, ValueError, TypeError):
                        pass
                # Imported WAVs may lack a sidecar; read duration from audio header.
                if not row.get("recording_seconds"):
                    try:
                        import soundfile as sf
                        row["recording_seconds"]=round(float(sf.info(str(path)).duration),2)
                    except Exception:
                        pass
                if 0 < float(row.get("recording_seconds") or 0) < 15:
                    note="Короткая запись. Для устойчивого тембра желательно 20–40 секунд чистого голоса без музыки."
                    row["recording_warning"]=(str(row.get("recording_warning") or "").strip()+" "+note).strip()
            rows.append(row)
    return rows

def compatible_audio(path):
    """Convert Windows Voice Recorder M4A/AAC to PCM WAV for ACE-Step.
    Cache the result; leave the original user recording untouched.
    """
    if path.suffix.lower() in (".wav", ".flac", ".mp3", ".ogg"):
        return path
    if path.suffix.lower() not in (".m4a", ".aac"):
        raise ValueError("Неподдерживаемый формат записи.")
    key = "%s_%s_%s.wav" % (path.stem, path.stat().st_size, path.stat().st_mtime_ns)
    output = NORMALIZED / safe_name(key)
    if output.is_file() and output.stat().st_size > 1024:
        return output
    partial = output.with_suffix(".part.wav")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(path), "-map", "0:a:0",
           "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(partial)]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 creationflags=flags, timeout=120, check=False)
        if process.returncode != 0 or not partial.is_file() or partial.stat().st_size < 1024:
            raise RuntimeError("Не удалось прочитать запись диктофона: " +
                               process.stderr.decode("utf-8", errors="replace")[-280:])
        partial.replace(output)
        return output
    finally:
        if partial.is_file():
            partial.unlink(missing_ok=True)


def training_progress():
    voice_files = list((ROOT / "Voice Engine" / "training_dataset" / "OWNER_VOICE").glob("alex_voice_*.wav"))
    model_file = VOICE_TRAINING / "ft_model.pth"
    raw = VOICE_TRAIN_LOG.read_bytes() if VOICE_TRAIN_LOG.exists() else b""
    if raw.startswith(bytes([255, 254])) or raw.count(bytes([0])) > len(raw) // 6:
        lines = raw.decode("utf-16", errors="replace")[-12000:]
    else:
        lines = raw.decode("utf-8", errors="replace")[-12000:]
    matches = re.findall(r"epoch\s+(\d+),\s+step\s+(\d+),\s+loss:\s+([0-9.]+)", lines)
    progress = int(matches[-1][1]) if matches else 0
    voice_status = voice_training.status()
    if voice_status["active"] or voice_status["exit_code"] is not None:
        progress = voice_status["step"]
    beat_files = [p for p in BEAT_SAMPLES.iterdir() if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".flac", ".ogg", ".m4a")]
    model_ready = model_file.is_file() and model_file.stat().st_size > 10000000
    if model_ready: progress = 100
    return {"voice_samples": len(voice_files), "voice_training_step": progress,
            "voice_training_running": voice_status["active"],
            "voice_training_message": voice_status["message"],
            "voice_training_exit_code": voice_status["exit_code"],
            "voice_training_total": 100, "voice_checkpoint_ready": model_ready,
            "beat_samples": len(beat_files), "beat_minimum": 8,
            "beat_training_ready": len(beat_files) >= 8,
            "status": "Готовая голосовая модель (ещё не проверена на слух)" if model_ready else
                      "Донастройка голоса или подготовка",
            "beat_directory": str(BEAT_SAMPLES)}

def export_audio(source, destination):
    result = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(source),
                             "-c:a", "libmp3lame", "-b:a", "320k", str(destination)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("Не удалось сохранить MP3: " + result.stderr.decode(errors="replace")[-220:])

def generate_worker(data, job_id):
    try:
        prepared = prepare_request(data)
        resolved_title, title_origin = resolve_title(data, workflow.lyric_status().get("variants", []))
        quality = "composer"
        is_turbo = True
        engine_url = ENGINE_URL
        engine_name = "Music Studio"
        update_job(status="preparing", message="Подготавливаем музыку...")
        ensure_unified_engine()
        config = http.get(engine_url + "/config", timeout=20).json()
        dep = next(x for x in config["dependencies"] if x.get("api_name") == "generation_wrapper")
        components = {x["id"]: x for x in config["components"]}

        duration_input = int(data.get("duration", 0) or 0)
        duration, duration_source = resolve_duration(duration_input, data.get("style", ""))
        prepared["duration_seconds"] = duration
        prepared["duration_source"] = duration_source
        if duration_source == "prompt":
            prepared["warnings"].append("Длительность указана в промпте: %d секунд. Ручная настройка имеет приоритет." % duration)
        bpm = int(data.get("bpm", 0) or 0)
        style_bpm = re.search(r"\b(\d{2,3})\s*BPM\b", str(data.get("style", "")), re.I)
        if bpm == 0 and style_bpm:
            bpm = int(style_bpm[1])
        if bpm and style_bpm and int(style_bpm[1]) != bpm:
            prepared["caption"] = re.sub(r"\b\d{2,3}\s*BPM\b", str(bpm)+" BPM", prepared["caption"], flags=re.I)
            prepared.setdefault("warnings", []).append("Ручной BPM имеет приоритет: конфликтующий темп в описании согласован с настройкой.")
        if bpm and not 30 <= bpm <= 300:
            raise ValueError("Укажи темп 30–300 BPM или 0 для автоматического выбора.")
        lyrics = prepared["lyrics"]
        instrumental = bool(data.get("instrumental", False))
        mode = str(data.get("mode", "new"))
        if instrumental:
            lyrics = "[Instrumental]"
        caption = str(data.get("style", "")).strip()
        if not caption:
            raise ValueError("Укажи музыкальный стиль.")
        if not instrumental and not lyrics:
            raise ValueError("Добавь слова песни или включи режим «Без вокала».")

        refs = {}
        voice_for_conversion = None
        voice_model_selection={"trained":False,"policy":"none","model":"none"}
        if data.get("use_voice") and data.get("voice"):
            v = basename_in(VOICES, str(data["voice"]))
            if v is None or not v.is_file():
                raise ValueError("Не найдена выбранная запись голоса.")
            artist_profile=voice_profiles34.validate_reference(v.name,data.get("voice_profile_id",""))
            prepared["voice_artist_profile"]=artist_profile
            voice_model_selection=select_voice_model(v,artist_profile)
            prepared["voice_model_selection"]=voice_model_selection
            voice_for_conversion = compatible_audio(v)
            # Reference Audio may confuse the lyric generator; use separate
            # Seed-VC postprocessing for faithful timbre transfer by default.
            if bool(data.get("style_reference", False)):
                refs["Reference Audio"] = handle_file(str(voice_for_conversion))
        if mode == "remix":
            src = basename_in(INPUTS, str(data.get("source", "")))
            if src is None or not src.is_file():
                raise ValueError("Для ремикса сначала загрузи исходную песню.")
            refs["Source Audio"] = handle_file(str(compatible_audio(src)))

        # Measure the chosen reference before composing, not only after singing.
        reference_profile = None
        if voice_for_conversion is not None and not instrumental:
            update_job(status="preparing", message="Определяем вокальный диапазон выбранной записи...")
            try:
                from voice_profile16 import profile
                reference_profile = profile(voice_for_conversion)
            except Exception as exc:
                reference_profile = {"reliable": False, "warning": str(exc)[:160]}
            # QA74: keep the measured low-register baritone guidance even
            # when the 512-character caption is already almost full.
            # Never replace a user-requested tenor/high singing direction.
            from voice_caption74 import integrate as integrate_reference_register
            caption74 = integrate_reference_register(prepared["caption"], reference_profile)
            prepared["caption"] = caption74["caption"]
            prepared["caption_length"] = len(prepared["caption"])
            prepared["reference_register_instruction"] = caption74
            prepared["reference_profile"] = reference_profile
        sample_reference = None  # Each independent take builds its own reference below.
        effect_requests = planned_effects(prepared.get("sections", []))
        # QA87: pass explicit user "No X" exclusions to the 5Hz LM's separate
        # negative channel, without editing the source lyrics or changing pitch.
        if not instrumental:
            from vocal_constraints87 import add_constraints, syllable_health
            vocal_exclusions = add_constraints(
                data.get("style", ""), prepared["vocal_language"], prepared.get("negative_prompt", ""))
            prepared["negative_prompt"] = vocal_exclusions["negative_prompt"]
            prepared["vocal_exclusion_audit"] = vocal_exclusions
            lyric_health = syllable_health(lyrics, duration)
            prepared["lyric_enunciation_budget"] = lyric_health
            if lyric_health.get("warning"):
                prepared.setdefault("warnings", []).append(lyric_health["warning"])
        settings = {
            "Music Caption": prepared["caption"],
            "Key": prepared["music_key"],
            "Time Signature": prepared.get("time_signature", ""),
            "__style_plan": prepared["style_plan"],
            "__use_trained_groove_reference": bool(data.get("use_trained_groove_reference", False)),
            "Lyrics": lyrics,
            "Audio Duration (seconds)": duration,
            "Batch Size": 2 if bool(data.get("two_versions", True)) else 1,
            "BPM (Beats Per Minute)": bpm if bpm else None,
            "Vocal Language": prepared["vocal_language"],
            "LM Negative Prompt": prepared["negative_prompt"],
            "DiT Inference Steps": 8 if is_turbo else (32 if quality == "sft" else 50),
            "DiT Guidance Scale (Base model only)": 7.0,
            "Shift": 3.0 if is_turbo else 1.0,
            "Random Seed": True,
            "Auto Score": False,
            "Auto LRC": bool(effect_requests) and not instrumental,
            "CoT Metas (Chain-of-Thought Metadata)": True,
            "CoT Language Detection": False,
            "CaptionRewrite": False,
            "Think": True,
            "Seed": "-1",
            "MP3 Bitrate": "256k",
            "Audio Format": "wav",
            "LM Temperature": 0.75,
            "LM Batch Chunk Size": 1,
            "Cover Strength (Melody Retention)": 0.6 if mode == "remix" else 0.0,
        }
        settings.update(refs)
        request_dir = APP / "requests"
        request_dir.mkdir(exist_ok=True)
        request_file = request_dir / (re.sub(r"[^a-zA-Z0-9_-]", "", str(job_id)) + ".json")
        request_file.write_text(json.dumps({"preparation": prepared,
            "voice_routing": {
                "voice_requested":bool(data.get("use_voice") and data.get("voice")),
                "apply_voice":bool(data.get("apply_voice",True)),
                "selected_recording":str(data.get("voice") or ""),
                "validated_profile_id":(prepared.get("voice_artist_profile") or {}).get("profile_id"),
                "trained":bool(voice_model_selection["trained"]),
                "model":voice_model_selection["model"],
                "policy":voice_model_selection["policy"],
                "pipeline":"convert_track_studio83.py"},
            "groove_reference_opt_in":bool(data.get("use_trained_groove_reference", False)),
            "settings": {key: value for key, value in settings.items() if key not in refs}},
            ensure_ascii=False, indent=2), encoding="utf-8")
        unique, lrc_by_sample, variant_records = compose_independent(
            settings, config, data.get("style", ""), mode, engine_url, job_id,
            lambda message: update_job(status="generating", message=message))
        sample_reference = any(record.get("reference") for record in variant_records)
        (request_dir / (str(job_id)+"_variants.json")).write_text(
            json.dumps(variant_records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        (request_dir / (str(job_id)+"_alignment.json")).write_text(
            json.dumps(lrc_by_sample, ensure_ascii=False, indent=2), encoding="utf-8")

        title = resolved_title
        stem = safe_name(title, "track")
        prefix = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(job_id)[:6]
        limit = 2 if bool(data.get("two_versions", True)) else 1
        want_voice = (voice_for_conversion is not None and not instrumental
                      and bool(data.get("apply_voice", True)))
        selected = unique[:limit]
        ready = []
        voice_warnings = []
        for index, path in enumerate(selected, 1):
            filename = prefix + "_" + stem + ("_" + str(index) if limit > 1 else "") + ".mp3"
            original_name = Path(filename).stem + Path(path).suffix.lower()
            original = ORIGINALS / original_name
            shutil.copy2(path, original)
            # Validate ACE-Step PCM before processing; reject broken DC-heavy output.
            from audio_guard55 import inspect_source
            inspect_source(original)
            if not want_voice:
                export_audio(original, TRACKS / filename)
                ready.append({"name": filename, "url": "/api/audio/" + filename,
                              "original_name": original_name, "original_url": "/api/original/" + original_name,
                              "title": title})
                continue

            # Never present the raw/converted pair as two generated tracks:
            # baseline remains available separately for A/B and archival use.
            result_name = original.stem + "_МОЙ_ГОЛОС.mp3"
            result_path = TRACKS / result_name
            try:
                # Seed-VC singing docs recommend 30-50 diffusion steps; favor stable quality.
                steps = 40
                convert_song(
                    original, voice_for_conversion, result_path,
                    on_stage=lambda message, idx=index:
                        update_job(status="converting", message="Вариант %d/%d: %s" %
                                   (idx, len(selected), message)),
                    steps=steps,
                    trained=voice_model_selection["trained"],
                    pitch_smooth=0.0,
                    register_mode="original",  # Preserve musical pitch.
                    vocal_language=prepared["vocal_language"],
                    chorus_ranges=chorus_windows(prepared.get("sections",[]),
                        lrc_by_sample.get(index,""),
                        __import__("soundfile").info(str(original)).duration)[0],
                )
                # The voice mixer can also fail independently of ACE-Step.
                # Never claim that the user's voice was applied if final audio is damaged.
                inspect_source(result_path)
                ready.append({
                    "name": result_name, "url": "/api/audio/" + result_name,
                    "original_url": "/api/original/" + original_name,
                    "original_name": original_name,
                    "master_url": "/api/master/" + Path(result_name).with_suffix(".wav").name,
                    "title": title, "variant": index, "voice_applied": True,
                    "voice_model_policy":voice_model_selection["policy"],
                    "voice_model_used":voice_model_selection["model"],
                    "voice_pipeline":"convert_track_studio83.py",
                    "voice_model_trained":bool(voice_model_selection["trained"]),
                })
            except Exception as voice_exc:
                # Do not lose a successful music generation if voice conversion fails.
                export_audio(original, TRACKS / filename)
                ready.append({
                    "name": filename, "url": "/api/audio/" + filename,
                    "title": title, "variant": index, "voice_applied": False,
                    "original_name":original_name,"original_url":"/api/original/"+original_name,
                    "voice_check_note":"Перенос тембра не применён: "+str(voice_exc),
                    "voice_model_policy":voice_model_selection["policy"],
                    "voice_model_used":voice_model_selection["model"],
                    "voice_model_trained":bool(voice_model_selection["trained"]),
                    "voice_pipeline":"convert_track_studio83.py",
                })
                voice_warnings.append("Вариант %d: %s" % (index, voice_exc))

        for item in ready:
            check_file=(TRACKS/item['name']).with_suffix('.voicecheck.json')
            if not check_file.is_file() and item.get('voice_applied') is False:
                check_file=(TRACKS/(Path(item['name']).stem+'_МОЙ_ГОЛОС.mp3')).with_suffix('.voicecheck.json')
            if check_file.is_file():
                measured=json.loads(check_file.read_text(encoding='utf-8'))
                item['voice_check_status']=measured['status']
                item['voice_check_note']=measured.get('reason','Автоматическая проверка не выявила грубой регрессии. Естественность не подтверждена.')
        production_warnings = []
        for take in variant_records:
            warning = take.get("groove_reference_warning")
            if warning and warning not in production_warnings:
                production_warnings.append(warning)
        if prepared.get("lyric_enunciation_budget",{}).get("warning"):
            production_warnings.append(prepared["lyric_enunciation_budget"]["warning"])
        for number, item in enumerate(ready, 1):
            item["acoustic_quality_verified"] = False
            take = variant_records[number-1]
            item["composition_seed"] = take["seed"]
            if take.get("reference"):
                item["sample_guided_808"] = bool(take["reference"] and take["reference"]["kind"] == "trained_groove24_sample_reference")
                item["learned_rhythm"] = bool(take["reference"].get("learned_weights_used"))
                item["rhythm_model_step"] = take["reference"].get("model_step")
                item["arrangement"] = {k: take["reference"]["plan"].get(k)
                    for k in ("key", "bpm", "progression_index", "groove_index")}
            else:
                item["sample_guided_808"] = False
            item["reference_source"] = take.get("reference_source", "none")
            if take.get("groove_reference_warning"):
                item["groove_reference_warning"] = take["groove_reference_warning"]
            item["automatic_minor_key_forced"] = bool(take.get("automatic_minor_key_forced"))
            if effect_requests:
                update_job(status="converting", message="Вариант %d/%d: сводим отдельную дорожку звуковых эффектов..." % (number, len(ready)))
                master = MASTERS / Path(item["name"]).with_suffix(".wav").name
                source = master if item.get("voice_applied") and master.is_file() else Path(selected[number-1])
                stem_file = ROOT / "Дорожки" / (Path(item["name"]).stem + "_FX.wav")
                report = render_effects(source, master, prepared, lrc_by_sample.get(number, ""), stem_file)
                export_audio(master, TRACKS / item["name"])
                item["master_url"] = "/api/master/" + master.name
                item["effects"] = report["effects_applied"]
                item["production_warnings"] = report["warnings"]
                item["fx_url"] = "/api/fx/" + stem_file.name
                production_warnings.extend("Вариант %d: %s" % (number, message) for message in report["warnings"])
                (TRACKS / item["name"]).with_suffix(".production.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        # Every take, even without SFX or voice conversion, receives a seamless
        # beginning/end, an archived 24-bit master and a documented finish.
        for ordinal,item in enumerate(ready,1):
            update_job(status="converting",message="Вариант %d/%d: плавное вступление, припевы и студийное завершение..."%(ordinal,len(ready)))
            target_master=MASTERS/Path(item["name"]).with_suffix(".wav").name
            source_master=target_master if target_master.is_file() else ORIGINALS/item["original_name"]
            from soundfile import info as audio_info
            song_seconds=float(audio_info(str(source_master)).duration)
            chorus_map,chorus_basis=chorus_windows(prepared.get("sections",[]),
                lrc_by_sample.get(ordinal,""),song_seconds)
            finished=finish_master34(source_master,target_master,chorus_ranges=chorus_map)
            finished["chorus_timing_basis"]=chorus_basis
            export_audio(target_master,TRACKS/item["name"])
            item["master_url"]="/api/master/"+target_master.name
            item["finishing"]=finished
            item["voice_profile_id"]=str(data.get("voice_profile_id","")) if item.get("voice_applied") else ""
            if item.get("voice_applied") and not item.get("voice_model_trained",False):
                item["voice_model_notice"]="Базовый перенос Seed-VC: выбранный образец не связан с персональным обученным чекпойнтом. Совпадение твоего тембра не подтверждено."
            (TRACKS/item["name"]).with_suffix(".finishing.json").write_text(
                json.dumps(finished,ensure_ascii=False,indent=2),encoding="utf-8")
        for item in ready:
            item["title_origin"] = title_origin
            item.setdefault("variant", ready.index(item)+1)
            # Persist *this take*, not whatever text is in the editor later.
            take = variant_records[item["variant"]-1]
            item["style_original"] = str(data.get("style", ""))
            item["lyrics_original"] = str(data.get("lyrics", ""))
            item["caption_sent"] = str(take.get("settings",{}).get("Music Caption", prepared["caption"]))
            item["lyrics_sent"] = str(settings["Lyrics"])
            item["style_plan"] = prepared["style_plan"]
            item["vocal_exclusion_audit"] = prepared.get("vocal_exclusion_audit",{})
            item["lyric_enunciation_budget"] = prepared.get("lyric_enunciation_budget",{})
            (TRACKS / item["name"]).with_suffix(".track.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            # Audio is available immediately. Artwork is queued separately.
            item["cover_url"] = "/api/cover/" + quote(item["name"])
            queue_cover(TRACKS / item["name"], background=True)
        message = "Готово! %d трек(а). Исходники сохранены отдельно." % len(ready)
        if voice_warnings:
            message = ("Сохранены %d трека; замена голоса не удалась: %s"
                       % (len(ready), "; ".join(voice_warnings)[:220]))
        if want_voice and not voice_model_selection["trained"]:
            message += " Использована базовая Seed-VC, не персональная обученная модель; сходство голоса не подтверждено."
        if production_warnings:
            message += " Требует проверки: " + "; ".join(production_warnings)[:350]
        record = {"requested": data, "engine_settings": settings, "variant_settings": variant_records,
                  "files": ready, "message": message, "version": "1.8"}
        (ORIGINALS / (prefix + "_" + stem + ".session.json")).write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        update_job(status="done", message=message, files=ready, title=title, title_origin=title_origin)
    except Exception as exc:
        update_job(status="error", message="Не удалось создать трек", error=str(exc))
        with WEBLOG.open("a", encoding="utf-8") as logfile:
            traceback.print_exc(file=logfile)

class Handler(BaseHTTPRequestHandler):
    server_version = "MusicStudio/1.9"

    def _report_internal_error(self, exc):
        error_id = uuid.uuid4().hex[:10]
        try:
            with WEBLOG.open("a", encoding="utf-8") as logfile:
                logfile.write("\n[SERVER_ERROR %s] %s %s: %s\n" %
                              (error_id, self.command, urlparse(self.path).path, type(exc).__name__))
                traceback.print_exc(file=logfile)
        except Exception:
            pass
        try:
            self.json(500, {"error": "Ошибка сервера Music Studio (%s, %s). "
                "Не запускай генерацию повторно вслепую; запусти scripts/Diagnose-Windows.ps1 "
                "и посмотри app/studio-server.log." % (type(exc).__name__, error_id),
                "error_id": error_id, "error_type": type(exc).__name__})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def do_GET(self):
        try:
            return self._do_GET()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return
        except Exception as exc:
            return self._report_internal_error(exc)

    def do_POST(self):
        try:
            return self._do_POST()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return
        except Exception as exc:
            return self._report_internal_error(exc)
    def log_message(self, fmt, *args):
        with WEBLOG.open("a", encoding="utf-8") as logfile:
            logfile.write("[%s] %s\n" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(data)

    def send_file(self, path):
        if not path.is_file():
            return self.json(404, {"error": "Файл не найден"})
        mime = "image/webp" if path.suffix.lower() == ".webp" else (mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        if path.suffix.lower() in (".html", ".css", ".js", ".txt"):
            mime += "; charset=utf-8"
        try:
            size = path.stat().st_size
            start, end, partial = 0, size - 1, False
            range_text = self.headers.get("Range")
            if range_text and path.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}:
                m = re.fullmatch(r"bytes=(\d*)-(\d*)", range_text.strip())
                if m:
                    a, b = m.groups()
                    if a:
                        start = int(a)
                        end = min(int(b), size-1) if b else size-1
                    elif b:
                        start = max(0, size-int(b))
                    if start >= size or end < start:
                        self.send_response(416)
                        self.send_header("Content-Range", "bytes */"+str(size))
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                    partial = True
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(end-start+1))
            self.send_header("Accept-Ranges", "bytes")
            if partial:
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command == "HEAD": return
            with path.open("rb") as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = source.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_HEAD(self):
        self.do_GET()

    def _do_GET(self):
        address = urlparse(self.path)
        path = address.path
        if path == "/api/sfx/catalog":
            from sound_catalog30 import stats, index
            from sound_bank29 import NAMES as synthetic_names
            payload = stats()
            payload["built_in_effects"] = list(synthetic_names) + ["sea surf"]
            payload["samples"] = [{"key":"sample:"+row["label"],"label":row["label"],
                                    "group":row["group"]} for row in index()[1]]
            return self.json(200, payload)
        if path == "/api/sfx/sample":
            from sound_effects29 import canonical as resolve_sound, _asset_path
            raw = parse_qs(address.query).get("key", [""])[0]
            if not raw or len(raw)>140:return self.json(400, {"error":"Некорректный идентификатор SFX"})
            kind = resolve_sound(raw)
            sample = _asset_path(kind) if kind else None
            if sample is None or not sample.is_file():return self.json(404, {"error":"Аудиоэффект не найден"})
            return self.send_file(sample)
        if path == "/api/health":
            connected = engine_ok()
            return self.json(200, {"ready": connected, "server_ready": True, "name": "Music Studio",
                                   "engine": engine_snapshot(connected),
                                   "job": copy_job(), "groove_reference": groove_availability(ROOT),
                                   "version": "1.10", "production_patch": "public-groove23-optional-preflight",
                                   "training23": training_reservation23.status(), "training41": training41_guard.status(),
                                   "training32": training32_guard.status(), "lyrics_busy": workflow.lyrics_active()})
        if path == "/api/diagnostics":
            # Loopback-only low-risk summary. Never include personal paths,
            # reference audio, generated lyrics or raw private log contents.
            return self.json(200, {"ok": True, "version": "1.9",
                                   "local_server": True, "engine": engine_snapshot(),
                                   "generator_installed": (ENGINE / ".venv" / "Scripts" / "acestep.exe").is_file(),
                                   "job_status": copy_job().get("status"),
                                   "diagnostic_command": "powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\Diagnose-Windows.ps1"})
        if path == "/api/presets/two-shores":
            preset_path = APP / "presets" / "two_shores.json"
            if not preset_path.is_file():
                return self.json(404, {"error": "Пример песни не найден"})
            return self.json(200, json.loads(preset_path.read_text(encoding="utf-8")))
        if path == "/api/lyrics":
            return self.json(200, workflow.lyric_status())
        if path == "/api/status":
            return self.json(200, copy_job())
        if path == "/api/voice-profiles":
            return self.json(200, voice_profiles34.list_profiles())
        if path == "/api/voices":
            return self.json(200, {"voices": media_list(VOICES)})
        if path == "/api/tracks":
            return self.json(200, {"tracks": media_list(TRACKS)})
        if path == "/api/settings/storage":
            return self.json(200, {"paths": storage_paths(ROOT)})
        if path == "/api/cover_status":
            name = parse_qs(address.query).get("name", [""])[0]
            target = basename_in(TRACKS, name)
            if target is None or target.suffix.lower() != ".mp3" or not target.is_file():
                return self.json(404, {"error":"Трек не найден"})
            return self.json(200, cover_info(target))
        if path == "/api/track_details":
            name = parse_qs(address.query).get("name", [""])[0]
            target = basename_in(TRACKS, name)
            if target is None or target.suffix.lower() not in (".wav",".mp3",".flac",".ogg",".m4a",".aac") or not target.is_file():
                return self.json(404, {"error": "Трек не найден."})
            return self.json(200, get_details(target.name, TRACKS, ORIGINALS))
        if path == "/api/training":
            return self.json(200, training_progress())
        if path == "/api/training41":
            return self.json(200, training41_guard.status())
        if path == "/qa100-compare":
            return self.send_file(UI / "qa100_compare.html")
        if path == "/api/qa100-audio/qa54":
            return self.send_file(ROOT / "Diagnostics" / "QA54" / "QA54_CFG090_35s.mp3")
        if path == "/api/qa100-audio/qa100":
            return self.send_file(ROOT / "Diagnostics" / "QA100-LowRegister" / "QA100_LowBaritone_MyVoice_35s.mp3")
        if path == "/qa90-style-compare":
            # Same-seed song A/B: original forced 808 reference vs native prompt.
            return self.send_file(UI / "qa90_style_compare.html")
        if path in ("/api/qa90-audio/forced", "/api/qa90-audio/native"):
            qa90 = ROOT / "Diagnostics" / "QA90-NativeStyle"
            fixed_audio = {
                "/api/qa90-audio/forced": qa90 / "with_auto_reference_70s_320.mp3",
                "/api/qa90-audio/native": qa90 / "no_reference_70s_320.mp3",
            }
            return self.send_file(fixed_audio[path])
        if path == "/qa86-sft-compare":
            # Read-only fixed-file comparison; no model mutation and no arbitrary paths.
            return self.send_file(UI / "qa86_sft_compare.html")
        if path in ("/api/qa86-audio/turbo", "/api/qa86-audio/sft"):
            qa86 = ROOT / "Diagnostics" / "QA86-SFTBenchmark"
            fixed = {
                "/api/qa86-audio/turbo": qa86 / "turbo_35s_320.mp3",
                "/api/qa86-audio/sft": qa86 / "sft_35s_320.mp3",
            }
            return self.send_file(fixed[path])
        if path == "/soulx-phonemes":
            # QA82 read-only phoneme comparison; explicit static local assets.
            return self.send_file(UI / "soulx-phonemes82.html")
        if path in ("/api/soulx-phonemes/qa78", "/api/soulx-phonemes/natural", "/api/soulx-phonemes/articulation"):
            preview_files = {
                "/api/soulx-phonemes/qa78": ROOT / "Diagnostics" / "QA78-SoulX-SungReference" / "QA78_SoulX_35s_320kbps.mp3",
                "/api/soulx-phonemes/natural": ROOT / "Diagnostics" / "QA82-ConsonantCompletion" / "QA82_Natural_35s_320kbps.mp3",
                "/api/soulx-phonemes/articulation": ROOT / "Diagnostics" / "QA82-ConsonantCompletion" / "QA82_Articulation_35s_320kbps.mp3",
            }
            return self.send_file(preview_files[path])
        if path == "/soulx-preview":
            # QA78: on-device comparisons; only predefined local assets.
            return self.send_file(UI / "soulx-preview78.html")
        if path in ("/api/soulx-preview/qa54", "/api/soulx-preview/qa77", "/api/soulx-preview/qa78"):
            previews = {
                "/api/soulx-preview/qa54": ROOT / "Diagnostics" / "QA54" / "QA54_CFG090_35s.mp3",
                "/api/soulx-preview/qa77": ROOT / "Diagnostics" / "QA77-SoulX-SVC" / "QA77_SoulX_35s_320kbps.mp3",
                "/api/soulx-preview/qa78": ROOT / "Diagnostics" / "QA78-SoulX-SungReference" / "QA78_SoulX_35s_320kbps.mp3",
            }
            return self.send_file(previews[path])
        if path == "/api/voice-qa/converted":
            # Explicit read-only local QA artifact. No arbitrary filename inputs.
            return self.send_file(ROOT / "Diagnostics" / "studio42" / "test42_long_personal_voice.mp3")
        if path == "/api/voice-qa/original":
            provenance = ROOT / "Diagnostics" / "studio42" / "test42_long_provenance.json"
            if not provenance.is_file():
                return self.json(404, {"error":"Тестовый исходник не найден"})
            saved = json.loads(provenance.read_text(encoding="utf-8"))
            source = basename_in(ORIGINALS, str(saved.get("source","")))
            return self.send_file(source or ORIGINALS / "_missing_")

        if path == "/api/inputs":
            return self.json(200, {"inputs": media_list(INPUTS)})
        if path == "/api/log":
            tail = WEBLOG.read_text(encoding="utf-8", errors="replace")[-12000:] if WEBLOG.exists() else ""
            return self.json(200, {"text": tail})
        if path.startswith("/api/cover/"):
            source = basename_in(TRACKS, path[len("/api/cover/"):])
            if source is None or source.suffix.lower() != ".mp3" or not source.is_file():
                return self.json(404, {"error": "Обложка не найдена"})
            try:
                image = generated_cover_path(source)
                if image.is_file():
                    return self.send_file(image)
                # Existing library artwork stays lightweight; only newly
                # generated tracks or an explicit retry queue GPU artwork.
                return self.send_file(ensure_cover(source))
            except Exception as exc:
                with WEBLOG.open("a", encoding="utf-8") as cover_log:
                    cover_log.write("COVER_RENDER_ERROR: "+str(exc)[:240]+"\\n")
                return self.json(500, {"error": "Не удалось создать обложку"})
        if path.startswith("/api/audio/"):
            return self.send_file(basename_in(TRACKS, path[len("/api/audio/"):]) or TRACKS / "_missing_")
        if path.startswith("/api/fx/"):
            directory = ROOT / "Дорожки"
            return self.send_file(basename_in(directory, path[len("/api/fx/"):]) or directory / "_missing_")
        if path.startswith("/api/master/"):
            return self.send_file(basename_in(MASTERS, path[len("/api/master/"):]) or MASTERS / "_missing_")
        if path.startswith("/api/original/"):
            return self.send_file(basename_in(ORIGINALS, path[len("/api/original/"):]) or ORIGINALS / "_missing_")
        if path.startswith("/api/voice/"):
            return self.send_file(basename_in(VOICES, path[len("/api/voice/"):]) or VOICES / "_missing_")
        if path == "/":
            return self.send_file(UI / "index.html")
        if path in ("/style.css", "/studio.js", "/workflow.js", "/unified.css", "/repair16.css", "/player17.js", "/player17.css", "/track_details26.css", "/pcm_recorder27.js", "/composer32.css", "/composer32.js", "/studio34.css", "/studio34.js", "/micro36.css", "/micro36.js", "/studio37.css", "/studio37.js", "/studio38.css", "/studio38.js", "/studio40.css", "/studio40.js", "/studio41.css", "/studio41.js", "/studio42.css", "/studio42.js", "/import_text29.js", "/sfx_palette30.js", "/studio_player31.css", "/voice_profiles34.js", "/voice_training76.js"):
            return self.send_file(UI / path[1:])
        self.json(404, {"error": "Страница не найдена"})

    def _do_POST(self):
        address = urlparse(self.path)
        path = address.path
        reserved = training_reservation23.status()
        if path in ("/api/generate", "/api/train_voice") and reserved["active"]:
            return self.json(409, {"error": reserved["message"]})
        model_run = training41_guard.status()
        if path in ("/api/generate", "/api/train_voice", "/api/lyrics") and model_run["active"]:
            return self.json(409, {"error": model_run["message"]})
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD:
            return self.json(413, {"error": "Файл пуст или слишком большой (макс. 90 МБ)."})
        if path == "/api/recording":
            if length > 20 * 1024 * 1024:
                return self.json(413, {"error": "Запись больше 20 МБ."})
            mime = self.headers.get("Content-Type", "").split(";")[0].lower()
            extensions = {"audio/webm":".webm", "video/webm":".webm", "audio/ogg":".ogg",
                          "audio/mp4":".m4a", "video/mp4":".m4a", "audio/wav":".wav", "audio/x-wav":".wav"}
            if mime not in extensions:
                return self.json(400, {"error": "Неподдерживаемый формат браузерной записи."})
            token = uuid.uuid4().hex
            raw = NORMALIZED / ("recording_" + token + extensions[mime])
            converted = NORMALIZED / ("recording_" + token + "_pcm.wav")
            try:
                content = self.rfile.read(length)
                if len(content) != length: raise ValueError("Запись загружена не полностью.")
                raw.write_bytes(content)
                analysis = workflow.normalize_recording(raw, converted)
                name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_Микрофон_" + token[:6] + ".wav"
                converted.replace(VOICES / name)
                (VOICES / (name + ".json")).write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
                return self.json(200, {"ok":True, "name":name, "analysis":analysis})
            except Exception as exc:
                return self.json(400, {"error":str(exc)})
            finally:
                raw.unlink(missing_ok=True); converted.unlink(missing_ok=True)
        if path == "/api/upload":
            query = parse_qs(address.query)
            kind = query.get("kind", ["voice"])[0]
            directory = VOICES if kind == "voice" else INPUTS if kind == "remix" else BEAT_SAMPLES if kind == "beat" else None
            if directory is None:
                return self.json(400, {"error": "Недопустимый тип записи"})
            original = query.get("name", ["audio.wav"])[0]
            ext = Path(original).suffix.lower()
            if ext not in (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"):
                return self.json(400, {"error": "Нужен MP3, WAV, FLAC, OGG, M4A или AAC."})
            name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6] + "_" + safe_name(original)
            dest = directory / name
            dest.write_bytes(self.rfile.read(length))
            return self.json(200, {"ok": True, "name": name, "size": length})
        if length > 180000:
            return self.json(413, {"error": "Слишком большой запрос."})
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self.json(400, {"error": "Неправильные данные"})
        if path == "/api/voice-profiles/create":
            try:
                artist=voice_profiles34.create_profile(data.get("name",""),data.get("permission") is True,data.get("language","ru"))
                return self.json(201,{"ok":True,"profile":artist})
            except (ValueError,TypeError) as exc:return self.json(400,{"error":str(exc)})
        if path == "/api/voice-profiles/assign":
            try:
                assigned=voice_profiles34.assign(data.get("voice",""),data.get("profile_id",""),data.get("permission") is True)
                return self.json(200,assigned)
            except (ValueError,TypeError) as exc:return self.json(400,{"error":str(exc)})
        if path == "/api/open-folder":
            try:
                result = open_storage_folder(ROOT, str(data.get("kind","")))
                return self.json(200, result)
            except (ValueError, RuntimeError) as exc:
                return self.json(400, {"error":str(exc)})
        if path == "/api/regenerate-cover":
            target = basename_in(TRACKS, str(data.get("name","")))
            if target is None or target.suffix.lower() != ".mp3" or not target.is_file():
                return self.json(404, {"error":"Трек не найден"})
            result = regenerate_cover(target)
            return self.json(202, result)
        if path == "/api/lyrics":
            with lock:
                if state["status"] in ("preparing", "generating", "converting") or voice_training.status()["active"]:
                    return self.json(409, {"error":"Сейчас создаётся музыка или обрабатывается голос. Повтори после завершения."})
                try:
                    jid, normalized = workflow.reserve_lyrics(data)
                except (ValueError, RuntimeError) as exc:
                    return self.json(400, {"error":str(exc)})
            threading.Thread(target=workflow.write_lyrics,
                             args=(normalized, jid, ensure_unified_engine, ENGINE_URL), daemon=True).start()
            return self.json(202, {"ok":True, "id":jid})
        if path == "/api/prepare":
            try:
                preview = prepare_request(data)
                if data.get("use_voice") and data.get("voice"):
                    path_voice = basename_in(VOICES, str(data["voice"]))
                    if path_voice is None or not path_voice.is_file():
                        raise ValueError("Выбранная запись голоса не найдена.")
                    verified = voice_profiles34.validate_reference(path_voice.name, data.get("voice_profile_id", ""))
                    selection = select_voice_model(path_voice, verified)
                    preview["voice_model_preview"] = {
                        "model": selection["model"],
                        "trained": bool(selection["trained"]),
                        "profile_id": verified.get("profile_id"),
                        "warning": ("" if selection["trained"] else
                            "Применится базовая Seed-VC, а не персональная модель; тембр может не совпасть."),
                        "perceptual_quality_verified": False,
                    }
                preview["groove_reference_opt_in"] = bool(data.get("use_trained_groove_reference", False))
                return self.json(200, preview)
            except (ValueError, TypeError) as exc:
                return self.json(400, {"error": str(exc)})
        if path == "/api/train_voice":
            with lock:
                if workflow.lyrics_active():
                    return self.json(409, {"error":"Сейчас создаются тексты."})
                if state["status"] in ("preparing", "generating", "converting"):
                    return self.json(409, {"error": "Сначала должна завершиться текущая генерация песни."})
                try:
                    result = voice_training.launch()
                    return self.json(202, {"ok": True, "training": result})
                except Exception as exc:
                    return self.json(409, {"error": str(exc)})
        if path == "/api/stop_voice_training":
            try:
                return self.json(200, {"ok": True, "training": voice_training.stop()})
            except Exception as exc:
                return self.json(500, {"error": str(exc)})
        if path == "/api/generate":
            try:
                if data.get("use_voice") and data.get("voice"):
                    voice_profiles34.validate_reference(str(data["voice"]),data.get("voice_profile_id",""))
                prepare_request(data)
            except (ValueError, TypeError) as exc:
                return self.json(400, {"error": str(exc)})
            with lock:
                if workflow.lyrics_active():
                    return self.json(409, {"error":"Сначала заверши создание двух вариантов текста."})
                if voice_training.status()["active"]:
                    return self.json(409, {"error": "Идёт обучение голоса на видеокарте. Останови его в разделе «Обучение моделей» перед генерацией."})
                if training32_guard.status()["active"]:
                    return self.json(409, {"error": "На видеокарте идёт дополнительное экспериментальное обучение Seed-VC. Рабочие треки сохранены; новая генерация недоступна до завершения."})
                if state["status"] in ("preparing", "generating", "converting"):
                    return self.json(409, {"error": "Уже создаётся трек. Дождись окончания."})
                # Worker starts the one unified engine on demand.
                state.update(id=uuid.uuid4().hex, status="preparing", message="Подготавливаем параметры...",
                             files=[], error="", started=datetime.now().isoformat())
                jid = state["id"]
            threading.Thread(target=generate_worker, args=(data, jid), daemon=True).start()
            return self.json(202, {"ok": True, "id": jid})
        if path == "/api/remove_track":
            name = str(data.get("name", ""))
            target = basename_in(TRACKS, name)
            if target is None or target.suffix.lower() != ".mp3" or not target.is_file():
                return self.json(404, {"error": "Трек не найден"})
            with lock:
                if state["status"] in ("preparing", "generating", "converting"):
                    return self.json(409, {"error": "Нельзя удалять треки во время генерации."})
                trash = ROOT / "Корзина треков"
                trash.mkdir(parents=True, exist_ok=True)
                token = uuid.uuid4().hex
                trashed = (datetime.now().strftime("%Y%m%d_%H%M%S")
                           + "_" + token[:8] + "_" + target.name)
                item = trash / trashed
                manifest = trash / ("undo_" + token + ".json")
                shutil.move(str(target), str(item))
                # Keep metadata and artwork in place: restoration is lossless.
                try:
                    manifest.write_text(json.dumps({
                        "name": target.name,
                        "trash_name": item.name,
                        "created": time.time(),
                    }, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    # Never invent a usable undo token if the manifest failed.
                    # Move the song back, as the deletion transaction failed.
                    shutil.move(str(item), str(target))
                    return self.json(500, {"error": "Не удалось подготовить отмену удаления"})
            return self.json(200, {"ok": True, "name": name,
                                   "moved_to_trash": True, "undo_token": token})
        if path == "/api/restore_track":
            token = str(data.get("token", ""))
            requested = str(data.get("name", ""))
            if not re.fullmatch(r"[0-9a-f]{32}", token):
                return self.json(400, {"error": "Неверный код восстановления"})
            with lock:
                if state["status"] in ("preparing", "generating", "converting"):
                    return self.json(409, {"error": "Дождись завершения генерации перед восстановлением"})
                trash = ROOT / "Корзина треков"
                manifest = trash / ("undo_" + token + ".json")
                if not manifest.is_file():
                    return self.json(404, {"error": "Восстановление не найдено или уже выполнено"})
                try:
                    info=json.loads(manifest.read_text(encoding="utf-8"))
                    original = str(info["name"])
                    stored = str(info["trash_name"])
                except (OSError, ValueError, TypeError, KeyError):
                    return self.json(400, {"error": "Повреждена запись восстановления"})
                if original != requested:
                    return self.json(400, {"error": "Трек не соответствует запросу"})
                source = basename_in(trash, stored)
                dest = basename_in(TRACKS, original)
                if dest is None or dest.suffix.lower() != ".mp3" or source is None:
                    return self.json(400, {"error": "Недопустимое имя трека"})
                if not source.is_file():
                    return self.json(404, {"error": "Файл удалён из корзины"})
                if dest.exists():
                    return self.json(409, {"error": "В библиотеке уже есть трек с таким именем"})
                shutil.move(str(source), str(dest))
                manifest.unlink(missing_ok=True)
            return self.json(200, {"ok": True, "name": original, "restored": True})
        if path == "/api/remove_voice":
            p = basename_in(VOICES, str(data.get("name", "")))
            if not p or not p.is_file():
                return self.json(404, {"error": "Файл не найден"})
            p.unlink()
            voice_profiles34.remove_assignment(p.name)
            return self.json(200, {"ok": True})
        return self.json(404, {"error": "Неизвестная команда"})

def main():
    if os.environ.get("MUSIC_STUDIO_DISABLE_ENGINE_AUTOSTART") != "1":
        threading.Thread(target=_background_start_engine, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print("MUSIC STUDIO READY http://127.0.0.1:%d" % PORT, flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()

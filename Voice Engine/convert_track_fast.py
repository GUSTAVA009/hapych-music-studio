"""Voice transfer pipeline for Music Studio.
1) isolate lead vocals with pretrained Demucs
2) convert isolated vocals to the user's reference timbre using pretrained Seed-VC
3) mix converted vocals with original instrumental, matching original duration
Designed for offline use after one-time model downloads.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
os.environ["no_proxy"] = "127.0.0.1,localhost,::1"
os.environ["PYTHONUTF8"] = "1"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VOICE = HERE / "seed-vc"
PYTHON = HERE / ".venv" / "Scripts" / "python.exe"
LOGFILE = HERE / "conversion.log"
WIP = HERE / "processing"
WIP.mkdir(exist_ok=True)

def say(message):
    print("STAGE:" + message, flush=True)

def execute(cmd, cwd=None, label="Команда"):
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with LOGFILE.open("a", encoding="utf-8", errors="replace") as logfile:
        logfile.write("\n=== %s ===\n" % label)
        logfile.write("EXECUTABLE: " + str(cmd[0]) + "\n")
        logfile.flush()
        result = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                                stdout=logfile, stderr=subprocess.STDOUT,
                                creationflags=flags, timeout=1800, check=False)
    if result.returncode:
        tail = LOGFILE.read_text(encoding="utf-8", errors="replace")[-2200:]
        raise RuntimeError("%s завершилась с ошибкой (%d): %s" % (label, result.returncode, tail[-700:]))

def probe_duration(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                            capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError("Не удалось прочитать длительность аудио: " + str(path))
    return float(result.stdout.strip())

def split_stems(song, destination):
    say("Отделяем голос от инструментальной дорожки...")
    execute([PYTHON, "-m", "demucs", "-n", "htdemucs", "--two-stems=vocals",
             "-d", "cuda", "--segment", "7", "-o", destination, song],
            label="Demucs vocal isolation")
    stems = destination / "htdemucs" / song.stem
    vocals, instrumental = stems / "vocals.wav", stems / "no_vocals.wav"
    if not vocals.is_file() or not instrumental.is_file():
        raise RuntimeError("Demucs не создал голосовую и инструментальную дорожки.")
    return vocals, instrumental

def split_vocals(vocals, work):
    parts = work / "parts"
    parts.mkdir(exist_ok=True)
    pattern = parts / "voice_%03d.wav"
    execute(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vocals,
             "-ac", "1", "-ar", "44100", "-f", "segment",
             "-segment_time", "16", "-reset_timestamps", "1", pattern],
            label="Split source vocals")
    clips = sorted(parts.glob("voice_*.wav"))
    if not clips:
        raise RuntimeError("Не удалось нарезать голосовую дорожку.")
    return clips

def convert_voice(clips, target, work, diffusion_steps):
    result = []
    for i, clip in enumerate(clips, 1):
        say("Переносим голос: фрагмент %d из %d..." % (i, len(clips)))
        output = work / ("converted_%03d" % i)
        output.mkdir(exist_ok=True)
        execute([PYTHON, "inference.py",
                 "--source", clip, "--target", target, "--output", output,
                 "--diffusion-steps", str(diffusion_steps),
                 "--f0-condition", "True", "--fp16", "True",
                 "--auto-f0-adjust", "False", "--semi-tone-shift", "0"],
                cwd=VOICE, label="Seed-VC %d/%d" % (i, len(clips)))
        found = sorted(output.glob("vc_*.wav"))
        if len(found) != 1:
            raise RuntimeError("Seed-VC не создал вокальную дорожку для фрагмента %d." % i)
        result.append(found[0])
    return result

def join_wav(clips, output, work):
    filelist = work / "concat.txt"
    # Filter_complex concat inputs avoids ffconcat file-path escaping on Windows.
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for clip in clips:
        args.extend(["-i", clip])
    for i in range(len(clips)):
        args += []  # no-op for clarity
    filters = "".join("[%d:a:0]aresample=44100,pan=mono|c0=c0[a%d];" % (i,i)
                      for i in range(len(clips)))
    filters += "".join("[a%d]" % i for i in range(len(clips)))
    filters += "concat=n=%d:v=0:a=1[voice]" % len(clips)
    args += ["-filter_complex", filters, "-map", "[voice]",
             "-c:a", "pcm_s16le", output]
    execute(args, label="Merge converted voice segments")

def mix_tracks(new_voice, backing, destination, duration):
    say("Сводим новый вокал и музыку...")
    # Pad short voice by silence and force original song length.
    # No automatic beat/tempo editing: the Seed-VC F0 variant follows original phrasing.
    filters = ("[0:a]aresample=44100,volume=1.08,apad[v];"
               "[1:a]aresample=44100,volume=0.90[inst];"
               "[v][inst]amix=inputs=2:duration=longest:normalize=0,"
               "alimiter=limit=0.94[out]")
    execute(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", new_voice, "-i", backing,
             "-filter_complex", filters, "-map", "[out]",
             "-t", "%.3f" % duration, "-c:a", "libmp3lame", "-b:a", "256k",
             "-ar", "44100", destination],
            label="Remix converted voice with backing track")
    if not destination.is_file() or destination.stat().st_size < 10000:
        raise RuntimeError("Не удалось сохранить итоговый MP3.")

def convert_full_voice(vocals, target, work, diffusion_steps):
    """Seed-VC handles the entire WAV with its own overlapping chunks.
    Single model load preserves continuity and avoids 16s discontinuities.
    """
    say("Переносим голос с сохранением музыкальных пауз...")
    destination = work / "converted_full"
    destination.mkdir(exist_ok=True)
    execute([PYTHON, "inference.py", "--source", vocals, "--target", target,
             "--output", destination,
             "--diffusion-steps", str(diffusion_steps), "--f0-condition", "True",
             "--fp16", "True", "--auto-f0-adjust", "False",
             "--semi-tone-shift", "0"],
            cwd=VOICE, label="Seed-VC full length")
    found = list(destination.glob("vc_*.wav"))
    if len(found) != 1:
        raise RuntimeError("Seed-VC не создал единую голосовую дорожку.")
    return found[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--steps", type=int, default=20)
    args = parser.parse_args()
    source, target, output = map(lambda p: Path(p).resolve(),
                                  (args.source, args.voice, args.output))
    if not source.is_file() or not target.is_file():
        raise RuntimeError("Исходный трек или образец голоса отсутствует.")
    if source.suffix.lower() not in {".mp3", ".wav", ".flac", ".m4a"}:
        raise RuntimeError("Неверный формат исходной песни.")
    if target.suffix.lower() != ".wav":
        raise RuntimeError("Образец голоса должен быть WAV.")
    if not 8 <= args.steps <= 60:
        raise RuntimeError("Некорректное число шагов диффузии.")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = WIP / ("song_" + uuid.uuid4().hex[:12])
    tmp.mkdir()
    try:
        duration = probe_duration(source)
        if duration > 610:
            raise RuntimeError("Песня длиннее 10 минут. Разбей её на части.")
        vocals, instrumental = split_stems(source, tmp / "stems")
        full_voice = convert_full_voice(vocals, target, tmp, args.steps)
        mix_tracks(full_voice, instrumental, output, duration)
        say("Готово! Новый голос добавлен в песню.")
        print(json.dumps({"ok":True,"output":str(output),"seconds":probe_duration(output)},
                         ensure_ascii=False),flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:" + str(exc), file=sys.stderr, flush=True)
        raise

from pathlib import Path
p=Path.home()/'Music Studio'/'Voice Engine'/'convert_track.py'
s=p.read_text(encoding='utf-8')
anchor='def main():\n'
assert s.count(anchor)==1
fast='''def convert_full_voice(vocals, target, work, diffusion_steps):
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

'''
s=s.replace(anchor,fast+anchor)
old='''        clips = split_vocals(vocals, tmp)
        converted = convert_voice(clips, target, tmp, args.steps)
        merged = tmp / "voice_merged.wav"
        join_wav(converted, merged, tmp)
        mix_tracks(merged, instrumental, output, duration)'''
new='''        full_voice = convert_full_voice(vocals, target, tmp, args.steps)
        mix_tracks(full_voice, instrumental, output, duration)'''
assert s.count(old)==1
s=s.replace(old,new)
dst=p.with_name('convert_track_fast.py')
dst.write_text(s,encoding='utf-8')
print('FAST_VOCAL_PROTOTYPE',dst)

"""QA51: preserve full style embedding while shortening *matched* prompt phonemes/mel/F0.
Fork only; no edits to production Seed-VC or its learned weights.
This corrects an earlier invalid dual-context attempt that mismatched S_ori vs mel2.
"""
from pathlib import Path
import py_compile,json,hashlib
R=Path.home()/"Music Studio";V=R/"Voice Engine";src=V/"seed-vc"/"inference_studio49.py";out=V/"seed-vc"/"inference_studio51.py"
s=src.read_text(encoding="utf-8")
changes=[
 ("    ori_waves_16k = torchaudio.functional.resample(ref_audio, sr, 16000)\n    S_ori = semantic_fn(ori_waves_16k)",
  "    # Use full 22s mic recording for CAMPPlus speaker *identity*, but a shorter\n"
  "    # internally consistent phonetic+pitch+mel acoustic prompt. Both pathways are\n"
  "    # kept separate, unlike the earlier invalid S_ori/mel2 length mismatch.\n"
  "    prompt_seconds = float(args.acoustic_prompt_seconds)\n"
  "    if not (8.0 <= prompt_seconds <= 25.0):\n"
  "        raise ValueError('acoustic prompt outside safe limits')\n"
  "    prompt_ref_audio = ref_audio[..., :int(sr * prompt_seconds)]\n"
  "    prompt_waves_16k = torchaudio.functional.resample(prompt_ref_audio, sr, 16000)\n"
  "    style_waves_16k = torchaudio.functional.resample(ref_audio, sr, 16000)\n"
  "    ori_waves_16k = prompt_waves_16k\n"
  "    S_ori = semantic_fn(prompt_waves_16k)"),
 ("    mel2 = mel_fn(ref_audio.to(device).float())",
  "    mel2 = mel_fn(prompt_ref_audio.to(device).float())"),
 ("    feat2 = torchaudio.compliance.kaldi.fbank(ori_waves_16k,",
  "    feat2 = torchaudio.compliance.kaldi.fbank(style_waves_16k,"),
 ("    max_source_window = max_context_window - mel2.size(2)",
  "    max_source_window = max_context_window - mel2.size(2)\n"
  "    register_report['qa51_reference_context'] = {\n"
  "        'style_seconds': round(float(ref_audio.shape[-1]/sr),3),\n"
  "        'prompt_seconds': round(float(prompt_ref_audio.shape[-1]/sr),3),\n"
  "        'prompt_semantic_frames': int(S_ori.shape[1]),\n"
  "        'prompt_mel_frames': int(mel2.shape[-1]),\n"
  "        'prompt_pitch_frames': int(F0_ori.shape[-1]) if F0_ori is not None else None,\n"
  "        'source_context_frames': int(max_source_window),\n"
  "        'aligned_acoustic_prompt': True,\n"
  "    }"),
 ("    parser.add_argument(\"--diffusion-steps\", type=int, default=30)",
  "    parser.add_argument(\"--diffusion-steps\", type=int, default=30)\n"
  "    parser.add_argument('--acoustic-prompt-seconds',type=float,default=15.0)"),
]
for a,b in changes:
 assert s.count(a)==1,("unrecognized upstream version",a[:90],s.count(a))
 s=s.replace(a,b)
out.write_text(s,encoding="utf-8");py_compile.compile(str(out),doraise=True)
orig=V/"convert_track_studio49.py";code=orig.read_text(encoding="utf-8")
assert code.count("inference_studio49.py")==1
code=code.replace("inference_studio49.py","inference_studio51.py")
a=" '--seed',str(a.seed)]"
# Make checkpoint and all core args stable; pass reference split as new inference flag.
key="'--seed',str(a.seed)]"
assert code.count(key)==1
code=code.replace(key,"'--seed',str(a.seed),'--acoustic-prompt-seconds','15.0']")
candidate=V/"convert_track_studio51.py"
candidate.write_text(code,encoding="utf-8");py_compile.compile(str(candidate),doraise=True)
diag=R/"Diagnostics"/"QA51";diag.mkdir(exist_ok=True,parents=True)
record={"source_inference_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
 "source_convert_sha256":hashlib.sha256(orig.read_bytes()).hexdigest(),
 "new_inference":str(out),"new_converter":str(candidate),
 "prompt_seconds":15,"style_seconds":22,"user_voice_reference_unchanged":True,
 "learned_weights_unchanged":True,"production_code_unchanged":True,
 "direct_alignment_of_semantic_mel_pitch":True}
(diag/"qa51_build.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA51_FORK_COMPILED",json.dumps(record,ensure_ascii=True),flush=True)

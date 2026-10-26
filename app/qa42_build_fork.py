"""Safely build QA42 experimental Seed-VC fork from known pristine sources.
No modifications to production inference.
"""
from pathlib import Path
import py_compile
ROOT=Path.home()/"Music Studio"/"Voice Engine"
SOURCE=ROOT/"seed-vc"/"inference_studio17.py"
FORK=ROOT/"seed-vc"/"inference_studio42.py"
CONVERT_SOURCE=ROOT/"convert_track_studio40.py"
CONVERT_FORK=ROOT/"convert_track_studio42.py"
s=SOURCE.read_text(encoding="utf-8")
changes=[
 ("    ori_waves_16k = torchaudio.functional.resample(ref_audio, sr, 16000)",
  "    ref_prompt_audio = ref_audio[..., :min(ref_audio.shape[-1],sr*13)]\n"
  "    ori_waves_16k = torchaudio.functional.resample(ref_prompt_audio, sr, 16000)\n"
  "    full_ref_waves_16k = torchaudio.functional.resample(ref_audio, sr, 16000)"),
 ("    mel2 = mel_fn(ref_audio.to(device).float())",
  "    mel2 = mel_fn(ref_prompt_audio.to(device).float())"),
 ("    feat2 = torchaudio.compliance.kaldi.fbank(ori_waves_16k,",
  "    feat2 = torchaudio.compliance.kaldi.fbank(full_ref_waves_16k,"),
 ("    max_source_window = max_context_window - mel2.size(2)",
  "    max_source_window = max_context_window - mel2.size(2)\n"
  '    register_report["reference_context42"] = {"speaker_embedding_seconds":float(ref_audio.shape[-1]/sr),'
  ' "acoustic_prompt_seconds":float(ref_prompt_audio.shape[-1]/sr),'
  ' "source_context_frames":int(max_source_window),'
  ' "mode":"full_reference_speaker_short_acoustic_prompt"}'),
]
for old,new in changes:
 count=s.count(old)
 assert count==1,(old,count)
 s=s.replace(old,new)
FORK.write_text(s,encoding="utf-8")
c=CONVERT_SOURCE.read_text(encoding="utf-8")
assert c.count("inference_studio17.py")==1
CONVERT_FORK.write_text(c.replace("inference_studio17.py","inference_studio42.py"),encoding="utf-8")
py_compile.compile(str(FORK),doraise=True)
py_compile.compile(str(CONVERT_FORK),doraise=True)
print("QA42_DUAL_CONTEXT_FORK_VERIFIED",FORK,CONVERT_FORK)

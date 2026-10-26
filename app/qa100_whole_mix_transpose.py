"""QA100: pitch-transpose WHOLE music + source voice together, preserving harmony,
then apply known QA54 Seed-VC personal checkpoint via ACTUAL current QA83 bridge.
No user track, model, studio code, or recordings overwritten.
No automatic production deployment without owner's listening approval.
"""
from pathlib import Path
import os,json,time,subprocess,hashlib,sys
import soundfile as sf
import numpy as np
import requests
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA100-LowRegister";D.mkdir(parents=True,exist_ok=True)
V=R/"Voice Engine";app=R/"app";sys.path.insert(0,str(app))
from voice_profiles34 import validate_reference
from voice_model_policy63 import select as model_select
from voice_bridge83 import convert_song
source=R/"Diagnostics"/"QA45"/"QA45_verse18to53.wav"
voice=next((R/"Мой голос").glob("*3867cb.wav"))
control=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.mp3"
assert source.is_file() and voice.is_file() and control.is_file()
selection=model_select(voice,validate_reference(voice.name,""))
assert selection["trained"] and selection["model"]=="alex_clean_qa44_v2",selection
session=requests.Session();session.trust_env=False
h=session.get("http://127.0.0.1:7870/api/health",timeout=10).json()
assert h["job"]["status"]=="idle",h["job"]
assert not any(h.get(k,{}).get("active") for k in ("training23","training41","training32"))
ratio=2**(-6/12)
musical_key_shift=-6
out_src=D/"QA100_WholeSong_Minus6semitones.wav"
out=D/"QA100_LowBaritone_MyVoice_35s.mp3"
cmd=["ffmpeg","-nostdin","-hide_banner","-v","error","-y",
 "-i",str(source),"-af",f"rubberband=pitch={ratio:.10f}:tempo=1:formant=preserved",
 "-ar","44100","-ac","2","-c:a","pcm_s24le",str(out_src)]
t=time.monotonic()
p=subprocess.run(cmd,capture_output=True,text=True,timeout=260)
assert p.returncode==0,p.stderr[-1800:]
orig_seconds=sf.info(source).duration
shift_seconds=sf.info(out_src).duration
assert abs(orig_seconds-shift_seconds)<.05,(orig_seconds,shift_seconds)
print("QA100_FULL_MIX_TRANSPOSED",round(time.monotonic()-t,2),
      "seconds",round(shift_seconds,3),"semitones",musical_key_shift,flush=True)
report={"test":"QA100 whole-song transposition before personal VC",
 "source":str(source),"source_hash":hashlib.sha256(source.read_bytes()).hexdigest(),
 "recording":str(voice),"model":selection,
 "semitones_music_and_voice":musical_key_shift,
 "pitch_ratio":ratio,"maintain_relative_harmony":True,
 "formant_option":"preserved","output_audio":str(out),
 "studio_production_code_unmodified":True,
 "originals_unmodified":True,"human_approved":False}
(D/"qa100_manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
log=D/"qa100_conversion.log"
with log.open("w",encoding="utf-8") as f:
 # Captured stdout while still using EXACT production bridge path 83.
 import contextlib
 with contextlib.redirect_stdout(f):
  try:
   converted=convert_song(out_src,voice,out,steps=40,trained=True,register_mode="original",vocal_language="ru")
  except Exception as e:
   print("QA100_CONVERT_ERROR",repr(e),flush=True)
   raise
assert out.is_file() and out.stat().st_size>100000
quality=json.loads(out.with_suffix(".quality.json").read_text(encoding="utf-8"))
check=quality["voice_check"]
report.update(
 duration_out_s=round(sf.info(out).duration,3),
 model_reported=quality.get("model"),
 output_pipeline=quality.get("pipeline_revision"),
 training_model_source=selection["policy"],
 vocal_guard_accepted=check.get("accepted"),
 vocal_guard_status=check.get("status"),
 detected_vocal_dips=check.get("metrics",{}).get("energy_dip_events"),
 longest_vocal_dip_s=check.get("metrics",{}).get("longest_energy_dip_s"),
 fraction_missing=check.get("metrics",{}).get("relative_missing_vocal_frames"),
 pitch_status=quality.get("pitch_consistency",{}).get("status"),
 register_audit=quality.get("register_audit83"))
(D/"qa100_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA100_ACTUAL_STUDIO_VOICE_CHAIN_OUTPUT",json.dumps({k:v for k,v in report.items() if k not in ("recording","source","source_hash","model","register_audit")},ensure_ascii=True),flush=True)

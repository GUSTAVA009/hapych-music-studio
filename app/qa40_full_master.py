"""QA40 full personal voice, SFX and non-destructive standalone master.
Only publish as a *technical listening test*, not proof of native voice identity.
"""
from pathlib import Path
import sys,json,ast,subprocess,re,hashlib
import soundfile as sf
R=Path.home()/"Music Studio";APP=R/"app";sys.path.insert(0,str(APP))
from studio_sections import prepare_request
from sound_effects29 import render_effects
from studio_finisher34 import finish
from chorus_layers34 import chorus_windows
D=R/"Diagnostics"/"QA40";D.mkdir(exist_ok=True,parents=True)
src=R/"Мастер WAV"/"QA40_Tikhiy_Svet_Full_22sRef_40steps.wav"
qfile=D/"QA40_Tikhiy_Svet_Full_22sRef_40steps.quality.json"
asr=D/"QA40_full_linguistic_qc.json"
assert src.is_file() and qfile.is_file() and asr.is_file()
q=json.loads(qfile.read_text(encoding="utf-8"))
ling=json.loads(asr.read_text(encoding="utf-8"))
guard=q["voice_check"]
metrics=guard["metrics"]
if not guard["accepted"] or q.get("pitch_consistency",{}).get("status")=="rejected":
 raise RuntimeError("Vocal transfer quality gate rejected")
if metrics["relative_missing_vocal_frames"]>.09 or metrics["longest_energy_dip_s"]>.35:
 raise RuntimeError("Excessive audio dropouts: not mastering")
if ling["relative_asr_edit_ratio"]>.48:
 raise RuntimeError("Large transcript mismatch: keep diagnostic audio only")
req=json.loads((R/"Diagnostics"/"QA38"/"request.json").read_text(encoding="utf-8"))
prepared=prepare_request(req)
result=json.loads((R/"Diagnostics"/"QA39"/"turbo_fixed_result.json").read_text(encoding="utf-8"))
lrc=result.get("sft_lrc","")
if lrc.startswith("{"):
 try:
  v=ast.literal_eval(lrc)
  if isinstance(v,dict):lrc=str(v.get("value") or "")
 except Exception:lrc=""
if not lrc.startswith("["):lrc=""
stem=D/"QA40_Full_MyVoice_SFX_only.wav"
premaster=D/"QA40_Full_MyVoice_SFX_prefade.wav"
fx=render_effects(src,premaster,prepared,lrc,stem)
if fx["effects_missing"]:raise RuntimeError("Missing SFX "+str(fx["effects_missing"]))
(D/"QA40_Full_fx_report.json").write_text(json.dumps(fx,ensure_ascii=False,indent=2),encoding="utf-8")
windows,basis=chorus_windows(prepared["sections"],lrc,float(sf.info(str(src)).duration))
finished=D/"QA40_Full_MyVoice_Finished.wav"
f=finish(premaster,finished,chorus_ranges=windows)
f["chorus_timing_basis"]=basis
(D/"QA40_Full_finish_report.json").write_text(json.dumps(f,ensure_ascii=False,indent=2),encoding="utf-8")
wav=D/"QA40_Tikhiy_Svet_MyVoice_Full_24bit.wav"
mp3=D/"QA40_Tikhiy_Svet_MyVoice_Full_320kbps.mp3"
norm="loudnorm=I=-13:LRA=11:TP=-1.4"
# Convert only final mix: no arbitrary 'de-robotize' notch in personal master.
first=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(finished),"-af",
 norm+":print_format=json","-f","null","NUL"],capture_output=True,text=True,timeout=180)
if first.returncode:raise RuntimeError(first.stderr[-1500:])
blocks=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',first.stderr,re.S)
assert blocks
base=json.loads(blocks[-1])
param={k:base[v] for k,v in [("measured_I","input_i"),("measured_TP","input_tp"),("measured_LRA","input_lra"),("measured_thresh","input_thresh"),("offset","target_offset")]}
extra=":".join(k+"="+str(v) for k,v in param.items())
second=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(finished),
 "-af",norm+":"+extra+":linear=true:print_format=json",
 "-ar","48000","-ac","2","-c:a","pcm_s24le",str(wav)],capture_output=True,text=True,timeout=180)
if second.returncode:raise RuntimeError(second.stderr[-1500:])
enc=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=120)
if enc.returncode:raise RuntimeError(enc.stderr[-1500:])
v=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(wav),
 "-af",norm+":print_format=json","-f","null","NUL"],capture_output=True,text=True,timeout=150)
blocks=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',v.stderr,re.S)
assert blocks
levels=json.loads(blocks[-1])
lufs=float(levels["input_i"]);peak=float(levels["input_tp"])
assert -16.0<lufs<-10.0 and peak<=-1.2,(lufs,peak)
info={"status":"technical_listening_test_not_certified_studio_voice",
 "wav":str(wav),"mp3":str(mp3),
 "duration_seconds":round(float(sf.info(str(wav)).duration),3),
 "integrated_lufs":lufs,"true_peak_dbtp":peak,
 "asr_relative_source_edit_fraction":ling["relative_asr_edit_ratio"],
 "speaker_cosine_proxy":q.get("speaker_embedding_cosine"),
 "vocal_frame_loss_ratio":metrics["relative_missing_vocal_frames"],
 "sfx_applied":[i["effect"] for i in fx["effects_applied"]],
 "all_srcs_untouched":True,"independent_backing_singers":False,
 "native_diction_certified":False,"voice_identity_certified":False,
 "mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest()}
(D/"QA40_full_master_report.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA40_FULL_READY",json.dumps(info,ensure_ascii=True),flush=True)

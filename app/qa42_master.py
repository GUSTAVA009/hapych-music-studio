"""QA39 alternate mastering: same-seed improved native vocal and grounded SFX.
Non-destructive and isolated in Diagnostics/QA39. No user's songs overwritten.
"""
from pathlib import Path
import sys,json,ast,subprocess,re,hashlib
import soundfile as sf
ROOT=Path.home()/"Music Studio";APP=ROOT/"app";sys.path.insert(0,str(APP))
from studio_sections import prepare_request
from sound_effects29 import render_effects
from studio_finisher34 import finish
from chorus_layers34 import chorus_windows
D=ROOT/"Diagnostics"/"QA42";D.mkdir(exist_ok=True,parents=True)
req=json.loads((D/"QA42_sung_request.json").read_text(encoding="utf-8"))["song"]
prepared=prepare_request(req)
source=D/"QA42_SungSource_160s_same_seed.wav"
assert source.is_file()
record=json.loads((D/"QA42_sung_result.json").read_text(encoding="utf-8"))
assert record["DiT_steps"]==8
text=""
if text.startswith("{"):
 try:
  value=ast.literal_eval(text)
  if isinstance(value,dict):text=str(value.get("value") or "")
 except (SyntaxError,ValueError):text=""
if not text.startswith("["):text=""
print("ALIGNMENT_CHARS",len(text),flush=True)
(D/"QA42_timestamp_text.lrc").write_text(text,encoding="utf-8")
stems=D/"QA42_SFX_bus.wav"
pre=D/"QA42_mixed_pre_finish.wav"
effects=render_effects(source,pre,prepared,text,stems)
assert not effects.get("effects_missing"), effects.get("effects_missing")
assert set(("rain_asphalt","car_pass"))<=set(x.get("effect") for x in effects["effects_applied"])
(D/"effects_report.json").write_text(json.dumps(effects,ensure_ascii=False,indent=2),encoding="utf-8")
print("SFX_APPLIED",[(x["effect"],x.get("start"),x.get("rendered_seconds")) for x in effects["effects_applied"]],flush=True)
fin=D/"QA42_mix_finished.wav"
windows,basis=chorus_windows(prepared["sections"],text,float(sf.info(str(pre)).duration))
finish_report=finish(pre,fin,chorus_ranges=windows)
finish_report["chorus_timing_basis"]=basis
(D/"finish_report.json").write_text(json.dumps(finish_report,ensure_ascii=False,indent=2),encoding="utf-8")
print("FINISHED",finish_report["finished_duration_seconds"],"CHORUSES",len(windows),"BASIS",basis,flush=True)
wav=D/"QA42_Tikhiy_Svet_24bit_Studio_Master.wav"
mp3=D/"QA42_Tikhiy_Svet_320k_Studio_Master.mp3"
prefix="highpass=f=26,equalizer=f=7600:t=q:w=0.75:g=-0.8"
norm="loudnorm=I=-13:LRA=11:TP=-1.4"
p=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(fin),"-af",prefix+","+norm+":print_format=json","-f","null","NUL"],
 capture_output=True,text=True,timeout=160)
if p.returncode:raise RuntimeError(p.stderr[-1200:])
blocks=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',p.stderr,re.S)
assert blocks,"Cannot measure mastering"
m=json.loads(blocks[-1])
keys={"measured_I":"input_i","measured_TP":"input_tp","measured_LRA":"input_lra","measured_thresh":"input_thresh","offset":"target_offset"}
extra=":".join(f"{k}={m[v]}" for k,v in keys.items())
q=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(fin),"-af",prefix+","+norm+":"+extra+":linear=true:print_format=json",
 "-ar","48000","-ac","2","-c:a","pcm_s24le",str(wav)],capture_output=True,text=True,timeout=180)
if q.returncode:raise RuntimeError(q.stderr[-1500:])
enc=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","320k",str(mp3)],
 capture_output=True,text=True,timeout=120)
if enc.returncode:raise RuntimeError(enc.stderr[-1200:])
val=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(wav),"-af",norm+":print_format=json","-f","null","NUL"],
 capture_output=True,text=True,timeout=120)
blocks=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',val.stderr,re.S)
assert blocks
v=json.loads(blocks[-1])
lufs=float(v["input_i"]);truepeak=float(v["input_tp"]);lra=float(v["input_lra"])
assert truepeak<=-1.20 and -15.5<=lufs<=-10.5,(lufs,truepeak)
r={"source":str(source),"master_wav":str(wav),"master_mp3":str(mp3),
 "duration_seconds":round(float(sf.info(str(wav)).duration),3),
 "wav_bytes":wav.stat().st_size,"mp3_bytes":mp3.stat().st_size,
 "wav_sha256":hashlib.sha256(wav.read_bytes()).hexdigest(),
 "mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
 "lufs":lufs,"true_peak_dbtp":truepeak,"loudness_range_lu":lra,
 "sfx":[{"name":x["effect"],"start":x["start"],"seconds":x["rendered_seconds"]} for x in effects["effects_applied"]],
 "chorus_width":finish_report.get("chorus_spatial_processing"),"vocal_backing_singers_independent":False,
 "natural_russian_pronunciation_verified":False,
 "original_qa38_preserved":True,"model":"ACE-Step Turbo v1.5","dit_steps":8}
(D/"QA42_master_report.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA42_MASTER_READY",json.dumps({k:r[k] for k in ("master_wav","master_mp3","duration_seconds","lufs","true_peak_dbtp","loudness_range_lu","mp3_sha256")},ensure_ascii=True),flush=True)

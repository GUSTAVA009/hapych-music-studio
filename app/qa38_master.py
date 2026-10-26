"""QA38 non-destructive two-pass music master and 320-kbps export.
Music keeps original arrangement/dynamics; tame sub-rumble and sharp upper treble.
Never replaces source tracks, mixes, models or voice recordings.
"""
from pathlib import Path
import subprocess,json,re,hashlib,os,time
R=Path.home()/"Music Studio"
D=R/"Diagnostics"/"QA38";D.mkdir(exist_ok=True,parents=True)
files=list((R/"Мастер WAV").glob("*QA38*_1.wav"))
assert len(files)==1,files
src=files[0]
dest=D/"Tikhiy_Svet_QA38_STUDIO_MASTER_24bit.wav"
mp3=D/"Tikhiy_Svet_QA38_STUDIO_MASTER_320kbps.mp3"
TARGET_I=-13.0;TARGET_LRA=11.0;TARGET_TP=-1.4
prefilter="highpass=f=26,equalizer=f=7600:t=q:w=0.75:g=-0.8"
normalizer="loudnorm=I=-13:LRA=11:TP=-1.4"
cmd=["ffmpeg","-hide_banner","-nostdin","-i",str(src),"-af",prefilter+","+normalizer+":print_format=json","-f","null","NUL"]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
if p.returncode:raise RuntimeError(p.stderr[-1200:])
matches=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',p.stderr,re.S)
assert matches,"Missing loudnorm measurements "+p.stderr[-1000:]
m=json.loads(matches[-1])
keys={"measured_I":"input_i","measured_TP":"input_tp","measured_LRA":"input_lra","measured_thresh":"input_thresh","offset":"target_offset"}
metrics=":".join(f"{k}={m[v]}" for k,v in keys.items())
filter2=prefilter+","+normalizer+":"+metrics+":linear=true:print_format=json"
q=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(src),"-af",filter2,
                  "-ar","48000","-ac","2","-c:a","pcm_s24le",str(dest)],capture_output=True,text=True,timeout=240)
if q.returncode:raise RuntimeError("Master pass2 "+q.stderr[-1500:])
r=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(dest),"-c:a","libmp3lame","-b:a","320k",str(mp3)],
                 capture_output=True,text=True,timeout=120)
if r.returncode:raise RuntimeError("MP3 "+r.stderr[-1200:])
meter=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(dest),"-af",
                      "loudnorm=I=-13:LRA=11:TP=-1.4:print_format=json","-f","null","NUL"],capture_output=True,text=True,timeout=120)
mm=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',meter.stderr,re.S)
assert mm, "No mastered validation stats"
actual=json.loads(mm[-1])
actual_i=float(actual["input_i"]);actual_tp=float(actual["input_tp"]);actual_lra=float(actual["input_lra"])
assert actual_tp<=-1.2,(actual_tp,actual)
assert -15.8 <=actual_i<=-10.5,(actual_i,actual)
info={"status":"mastered","original":str(src),"master":str(dest),"mp3":str(mp3),
      "source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
      "mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
      "target_lufs":TARGET_I,"target_tp_dbtp":TARGET_TP,
      "measured_lufs":actual_i,"measured_true_peak_dbtp":actual_tp,"measured_lra_lu":actual_lra,
      "source_measurement":m,"output_measurement":actual,
      "filters":["26Hz high pass","subtle -0.8dB wide band 7.6kHz","two-pass EBU R128 loudness normalization"],
      "user_source_files_unchanged":True,"perceptual_quality_verified":False,
      "publisher_claim":"technical mastering is complete; Russian diction not certified"}
(D/"final_master_report.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA38_MASTER_SUCCESS",json.dumps({k:info[k] for k in ["status","mp3","measured_lufs","measured_true_peak_dbtp","measured_lra_lu","mp3_sha256"]},ensure_ascii=True),flush=True)

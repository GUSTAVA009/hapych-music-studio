"""QA45 careful two-pass soft pop master; does not claim to cure neural accents.
"""
from pathlib import Path
import subprocess,re,json,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA45"
src=D/"QA45_NeoSoul_source.wav";assert src.is_file()
wav=D/"QA45_Tam_Gde_Teplo_24bit_Studio_Master.wav"
mp3=D/"QA45_Tam_Gde_Teplo_320kbps.mp3"
# Static damping of low rumble, soft airy top, gently balanced loudness.
eq="highpass=f=28,equalizer=f=3500:t=q:w=1.0:g=-0.7"
norm="loudnorm=I=-13.5:LRA=11:TP=-1.5"
a=subprocess.run(["ffmpeg","-nostdin","-i",str(src),"-af",eq+","+norm+":print_format=json",
 "-f","null","NUL"],capture_output=True,text=True,timeout=160)
assert a.returncode==0,a.stderr[-1500:]
matches=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',a.stderr,re.S)
assert matches
m=json.loads(matches[-1])
mappings={"measured_I":"input_i","measured_TP":"input_tp","measured_LRA":"input_lra",
          "measured_thresh":"input_thresh","offset":"target_offset"}
extra=":".join(f"{k}={m[v]}" for k,v in mappings.items())
b=subprocess.run(["ffmpeg","-nostdin","-y","-i",str(src),"-af",eq+","+norm+":"+extra+":linear=true:print_format=json",
 "-ar","48000","-ac","2","-c:a","pcm_s24le",str(wav)],capture_output=True,text=True,timeout=180)
assert b.returncode==0,b.stderr[-1500:]
c=subprocess.run(["ffmpeg","-nostdin","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","320k",str(mp3)],
 capture_output=True,text=True,timeout=120)
assert c.returncode==0,c.stderr[-1000:]
v=subprocess.run(["ffmpeg","-nostdin","-i",str(wav),"-af",norm+":print_format=json","-f","null","NUL"],
 capture_output=True,text=True,timeout=160)
result=json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}',v.stderr,re.S)[-1])
lufs=float(result["input_i"]);tp=float(result["input_tp"])
assert -16<lufs<-11 and tp<=-1.2,(lufs,tp)
duration=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
 "-of","default=noprint_wrappers=1:nokey=1",str(mp3)],capture_output=True,text=True,check=True).stdout)
info={"song":"Там, где тепло","model":"ACE-Step Turbo","source":str(src),
 "wav":str(wav),"mp3":str(mp3),"duration_s":round(duration,2),
 "lufs":lufs,"true_peak_dbtp":tp,"mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
 "uses_user_voice":False,"no_autotune":True,"automated_native_accent_verified":False,
 "source_untouched":True}
(D/"qa45_master_report.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA45_MASTER_READY",json.dumps(info,ensure_ascii=True),flush=True)

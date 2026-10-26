"""Simple reproducible CPU audio metrics for QA133.
No claim of perceptual timbre matching; no training or modification.
"""
from pathlib import Path
import json,sys,numpy as np,soundfile as sf
from math import gcd
from scipy.signal import resample_poly
import parselmouth
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
D=R/"Integrations"/"OpenUtau-QA129"/"QA132-KogdaPronunciation"/"QA133-FinalDiction"
P=D/"QA133-OwnerVoice"
report=json.loads((P/"QA133_owner_transfer.json").read_text(encoding="utf8"))
src=Path(report["source"])
def load16(file):
 y,sr=sf.read(file,dtype="float32",always_2d=True)
 y=y.mean(1)
 if sr!=16000:
  f=gcd(sr,16000);y=resample_poly(y,16000//f,sr//f).astype("float32")
 return y
source=load16(src)
hop=160
def env(y):
 n=len(y)//hop
 return np.sqrt(np.mean(y[:n*hop].reshape(n,hop).astype("float64")**2,axis=1)+1e-14)
e_src=env(source)
def f0(y):
 pitch=parselmouth.Sound(y,16000).to_pitch(time_step=.01,pitch_floor=65,pitch_ceiling=400)
 vals=np.array(pitch.selected_array["frequency"],dtype="float64")
 return vals
p_src=f0(source)
def gate(y):
 e=env(y);m=min(len(e),len(e_src))
 active=e_src[:m]>max(.006,float(np.quantile(e_src,.7))*.28)
 valid=active&(e[:m]>.0008)
 scale=float(np.median(e_src[:m][valid]/e[:m][valid])) if valid.sum()>50 else 1.0
 lost=active&(e[:m]*scale<e_src[:m]*.20)
 dif=np.diff(np.r_[0,lost.astype(int),0])
 a=np.where(dif==1)[0];b=np.where(dif==-1)[0]
 gaps=[(round(i*.01,2),round(j*.01,2)) for i,j in zip(a,b) if j-i>=7]
 f=p_src;g=f0(y);m2=min(len(f),len(g))
 voiced=(f[:m2]>65)&(g[:m2]>65)
 cents=1200*np.log2(g[:m2][voiced]/f[:m2][voiced])
 return {"duration":round(len(y)/16000,3),
  "peak":round(float(np.max(abs(y))),5),"rms":round(float(np.sqrt(np.mean(y.astype("float64")**2))),5),
  "clip_fraction":round(float(np.mean(abs(y)>=.998)),8),
  "dropout_intervals_gt70ms":gaps[:12],"dropout_count_gt70ms":len(gaps),
  "F0_matched_frames":int(voiced.sum()),
  "median_F0_abs_deviation_cents":round(float(np.median(np.abs(cents))),1) if len(cents) else None,
  "p90_F0_abs_deviation_cents":round(float(np.quantile(np.abs(cents),.90)),1) if len(cents) else None}
out={"status":"acoustics_screened_not_human_verified","cases":{}}
for tag,row in report["candidates"].items():
 y=load16(row["wav"])
 assert abs(len(y)/16000-20.88)<.07
 metrics=gate(y)
 out["cases"][tag]=metrics
 print("QA133_METRICS",tag,json.dumps(metrics,ensure_ascii=False),flush=True)
(P/"QA133_objective_metrics.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")

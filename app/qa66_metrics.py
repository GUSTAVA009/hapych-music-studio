"""QA66 objective 10ms stability audit across identical source vocals.
Measures excess sudden magnitude/modulation relative to original sung consonants.
It is a screen, NOT a perceptual or voice-identity certification.
"""
from pathlib import Path
import json, numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA66"
q=R/"Diagnostics"/"QA54"
original=q/"QA54_CFG090_35s.source.wav"
control=list((R/"Diagnostics"/"QA61"/"original_vocoder").glob("vc_*.wav"))
assert len(control)==1
new=json.loads((D/"qa66_generation_report.json").read_text(encoding="utf-8"))
paths={"source_ACE":original,"QA54_raw_control":control[0]}
for item in new:
 if item["exit_code"]==0:
  paths["QA66_"+item["name"]]=Path(item["audio"])
x,sr=sf.read(original,dtype="float32",always_2d=True)
assert sr==44100
n=len(x)
hop=441
def frame_db(audio):
 mono=audio.mean(axis=1)
 mono=mono[:n]
 if len(mono)<n:mono=np.pad(mono,(0,n-len(mono)))
 # Overlapping 30ms window evaluated every 10ms
 sq=mono.astype(float)**2
 f=np.sqrt(gaussian_filter1d(sq,sigma=0.012*sr,mode="reflect")[::hop]+1e-11)
 return 20*np.log10(f+1e-8)
src=frame_db(x)
activity=src>max(-47,float(np.percentile(src,80))-22)
# Compare on stable source syllable interiors: no source changes > 2.2dB/20ms
src_delta=np.abs(src[2:]-src[:-2])
stable=activity[1:-1]&(src_delta<2.5)
data={}
for label,p in paths.items():
 y,fs=sf.read(p,dtype="float32",always_2d=True)
 assert fs==sr
 level=frame_db(y)
 length=min(len(level),len(src))
 use=stable[:length-2]
 contrast=level[:length]-src[:length]
 baseline=np.median(contrast[1:length-1][use])
 delta=contrast-baseline
 sudden=np.abs(delta[2:]-delta[:-2])
 # 20ms sharp level changes in converted result with unchanged source song loudness
 new_jump=sudden[use]>6
 excessive=sudden[use]>9
 loss=(delta[1:length-1][use]<-9.0)
 ratio=float(np.mean(loss))
 # distinct burst event counts requiring >= 2 adjacent 10ms frames
 event_positions=np.flatnonzero((sudden>9.0)&use) if len(use) else []
 def runs(position,seconds_per_frame=.01):
  pos=np.asarray(position,dtype=int)
  if not len(pos):return []
  br=np.flatnonzero(np.diff(pos)>1)+1
  seq=np.split(pos,br)
  return [{"start_sec":round(float(g[0])*seconds_per_frame,3),
           "length_ms":round(float(len(g)*10),1)} for g in seq if len(g)>1]
 peaks=runs(event_positions)
 r={"duration_s":round(len(y)/sr,2),
    "src_stable_frame_count":int(use.sum()),"rms_relative_db":round(float(baseline),2),
    "weak_frames_below_minus9db_fraction":round(ratio,5),
    "abrupt_level_change_gt6db_20ms_fraction":round(float(np.mean(new_jump)),5),
    "abrupt_level_change_gt9db_20ms_fraction":round(float(np.mean(excessive)),5),
    "sharp_events_count":len(peaks),"worst_sharp_events":sorted(peaks,key=lambda z:z["length_ms"],reverse=True)[:10],
    "speech_certified":False}
 data[label]=r
 print("QA66_STABILITY",label,json.dumps(r,ensure_ascii=True),flush=True)
(D/"qa66_stability_comparison.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

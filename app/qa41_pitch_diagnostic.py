"""QA41 diagnose fast pitch modulation and abrupt F0 jumps on dry source/converted.
F0 from librosa.yin is a noisy proxy; analysis does NOT prove perceptual vibrato.
No output audio is altered.
"""
import json
from pathlib import Path
import numpy as np,soundfile as sf,librosa
from scipy.ndimage import gaussian_filter1d,median_filter
from scipy.signal import welch
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA41";D.mkdir(exist_ok=True,parents=True)
Q=R/"Diagnostics"/"QA40"
sources={
 "base_original":Q/"QA40_MyVoice_22secRef_40steps.source.wav",
 "vc_12sec":Q/"QA40_MyVoice_12secRef_40steps.dry.wav",
 "vc_22sec":Q/"QA40_MyVoice_22secRef_40steps.dry.wav",
}
out=[]
for name,path in sources.items():
 y,sr=sf.read(path,always_2d=True,dtype="float32");y=y.mean(axis=1)
 sub=librosa.resample(y,orig_sr=sr,target_sr=8000)
 hop=80;fps=8000/hop
 f0=librosa.yin(sub,sr=8000,fmin=65,fmax=500,frame_length=2048,hop_length=hop,trough_threshold=.12)
 rms=librosa.feature.rms(y=sub,frame_length=2048,hop_length=hop,center=True)[0]
 n=min(len(f0),len(rms));f0=f0[:n];rms=rms[:n]
 act=rms>max(.002,float(np.percentile(rms,87))*.28)
 med=np.median(f0[act]) if act.any() else 100
 cents=1200*np.log2(np.maximum(f0,1)/med)
 dc=np.diff(cents)
 adjacent=act[1:]&act[:-1]
 jump_count=int(np.count_nonzero((np.abs(dc)>450)&adjacent))
 sudden_250=int(np.count_nonzero((np.abs(dc)>250)&adjacent))
 # 0.5s trend-subtracted modulation amplitude; band-limited to 3.5-13Hz
 trend=gaussian_filter1d(cents,sigma=27)
 resid=cents-trend
 windows=[]
 for begin in range(0,int(n/fps)-2,2):
  a=int(begin*fps);b=int((begin+2)*fps)
  if b>n or float(np.mean(act[a:b]))<.65:continue
  t=resid[a:b]-np.mean(resid[a:b])
  freqs,P=welch(t,fs=fps,nperseg=min(200,len(t)))
  bands=(freqs>=4)&(freqs<=12)
  total=(freqs>=.5)&(freqs<=20)
  vibr=float(np.trapz(P[bands],freqs[bands])) if bands.sum()>1 else 0
  overall=float(np.trapz(P[total],freqs[total])) if total.sum()>1 else 1.
  windows.append({"start_s":begin,"vibrato_4to12hz_rms_cents":round(np.sqrt(vibr),1),
    "fast_band_fraction":round(vibr/max(overall,.01),3),
    "max_pitch_span_cents":round(float(np.percentile(cents[a:b],95)-np.percentile(cents[a:b],5)),1)})
 result={"name":name,"seconds":round(len(y)/sr,2),"voiced_fraction_proxy":round(float(act.mean()),3),
    "median_f0_hz":round(float(med),2),
    "f0_jump_over_450c_10ms":jump_count,"f0_jump_over_250c_10ms":sudden_250,
    "median_fast_vibrato_rms_cents":round(float(np.median([w["vibrato_4to12hz_rms_cents"] for w in windows])),2) if windows else None,
    "top_fast_modulation_windows":sorted(windows,key=lambda v:v["vibrato_4to12hz_rms_cents"],reverse=True)[:7]}
 print("PITCH_DIAG",json.dumps(result,ensure_ascii=True),flush=True)
 out.append(result)
(D/"pitch_diagnostics.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")

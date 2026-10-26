"""QA40 static spectrum survey on known vocal STEMS, before notch decisions.
Does not claim to prove subjective resonances; returns candidate broad formants.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json
from scipy.signal import welch,find_peaks,savgol_filter
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA40"
paths={
 "QA39_source_vocal":D/"QA40_MyVoice_22secRef_40steps.source.wav",
 "QA40_longref_finished_vocal":D/"QA40_MyVoice_22secRef_40steps.finished.wav",
 "QA40_shortref_finished_vocal":D/"QA40_MyVoice_12secRef_40steps.finished.wav",
 "user_reference":next((R/"Мой голос").glob("*df413d.wav")),
}
results={}
for k,p in paths.items():
 x,sr=sf.read(str(p),dtype="float32",always_2d=True)
 y=x.mean(axis=1)
 f,power=welch(y,sr,nperseg=8192,noverlap=4096)
 db=10*np.log10(np.maximum(power,1e-15))
 # Average 1/2-octave local background on log-frequency axis.
 freqs=np.geomspace(120,9000,512)
 envelope=np.interp(freqs,f,db)
 smooth=savgol_filter(envelope,83,2)
 detail=envelope-smooth
 peaks,params=find_peaks(detail,prominence=1.0,distance=12)
 peaks=sorted(peaks,key=lambda n:detail[n],reverse=True)
 candidate=[{"hz":round(float(freqs[i])),"excess_db":round(float(detail[i]),2)} for i in peaks if 350<=freqs[i]<=7500][:12]
 bands={}
 for a,b in [(150,350),(350,650),(650,1100),(1100,1800),(1800,2900),(2900,4500),(4500,7000),(7000,10000)]:
  mask=(f>=a)&(f<b)
  bands[f"{a}-{b}"]=round(float(10*np.log10(max(1e-20,np.trapz(power[mask],f[mask])))),2)
 results[k]={"file":str(p),"seconds":round(len(y)/sr,1),"spectral_peaks":candidate,"band_energy_dbfs":bands}
 print("SPECTRAL",k,json.dumps(results[k],ensure_ascii=True),flush=True)
(D/"QA40_spectrum_report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")

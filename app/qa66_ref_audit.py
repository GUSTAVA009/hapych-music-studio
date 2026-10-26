from pathlib import Path
import numpy as np, soundfile as sf,json
R=Path.home()/"Music Studio";p=R/"Diagnostics"/"QA57"/"reference_selected.wav"
x,sr=sf.read(p,dtype="float32",always_2d=True)
y=x.mean(axis=1); fs=sr//50
z=y[:len(y)//fs*fs].reshape(-1,fs)
ener=np.sqrt(np.mean(z.astype("float64")**2,axis=1)+1e-12)
threshold=max(.003,float(np.percentile(ener,75))*.20)
data=[]
for start in np.arange(0,max(.001,len(y)/sr-8.0),.5):
 clip=ener[round(start*50):round((start+8)*50)]
 if len(clip)<400:continue
 data.append({"start_sec":round(float(start),2),"active":round(float(np.mean(clip>threshold)),3),
 "rms_dbfs":round(float(20*np.log10(max(float(np.sqrt(np.mean(clip**2))),1e-7))),2),
 "quietest_rms":round(float(np.percentile(clip,15)),4),
 "max_amp":round(float(np.max(np.abs(y[round(start*sr):round((start+8)*sr)]))),4)})
choices=sorted(data,key=lambda t:(t["active"],t["quietest_rms"]),reverse=True)
print("REF_22SEC",json.dumps({"seconds":len(y)/sr,"energy_threshold":round(threshold,5),
"first8":data[0],"best8":choices[:4]},ensure_ascii=True),flush=True)
D=R/"Diagnostics"/"QA66";D.mkdir(parents=True,exist_ok=True)
(D/"qa66_ref_audit.json").write_text(json.dumps({"first8":data[0],"best":choices[:10]},indent=2),encoding="utf-8")

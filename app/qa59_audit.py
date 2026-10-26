"""QA59 single-speaker microphone data audit. No writes outside Diagnostics."""
from pathlib import Path
import numpy as np,soundfile as sf,hashlib,json
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";D.mkdir(exist_ok=True,parents=True)
files=[next((R/"Мой голос").glob("*"+q+".wav")) for q in ("df413d","3867cb","3ab452","65f5f3")]
items=[]
for p in files:
 x,sr=sf.read(p,dtype="float32",always_2d=True)
 mono=x.mean(axis=1);peak=float(abs(x).max())
 rms=float(np.sqrt(np.mean(mono**2)+1e-12))
 frame=int(sr*.025);count=len(mono)//frame
 energies=np.sqrt(np.mean(mono[:count*frame].reshape(count,frame)**2,axis=1)+1e-12)
 lower=float(np.percentile(energies,10));upper=float(np.percentile(energies,85))
 clipped=float(np.mean(abs(mono)>.985))
 active=float(np.mean(energies>max(lower*2.7,upper*.16)))
 item={"file":p.name,"sample_rate":sr,"channels":x.shape[1],"seconds":round(len(mono)/sr,3),
    "peak_dbfs":round(20*np.log10(max(peak,1e-9)),2),
    "rms_dbfs":round(20*np.log10(max(rms,1e-9)),2),
    "noise_p10_dbfs":round(20*np.log10(max(lower,1e-9)),2),
    "active_p85_dbfs":round(20*np.log10(max(upper,1e-9)),2),
    "frame_active_fraction":round(active,3),"clipped_fraction":round(clipped,6),
    "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
    "use":"holdout" if p.stem.endswith("65f5f3") else "train"}
 items.append(item)
 print("QA59_MIC_AUDIT",json.dumps(item,ensure_ascii=True),flush=True)
(D/"qa59_audio_audit.json").write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")

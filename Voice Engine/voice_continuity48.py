"""Conservative short-duration gain rescue for Seed-VC.
Never splice another singer, gate breath or alter pitch/timing.
Repairs a low-level converted phrase only where converted phonemes remain.
"""
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d
from scipy.signal import resample_poly
from math import gcd

def _frames(audio,hop):
    x=np.asarray(audio,dtype=np.float64)
    missing=(-len(x))%hop
    if missing:x=np.pad(x,(0,missing))
    return np.sqrt(np.mean(x.reshape(-1,hop)**2,axis=1)+1e-12)
def repair(source,converted,target):
    a,sr_a=sf.read(str(source),dtype="float32",always_2d=True)
    b,sr_b=sf.read(str(converted),dtype="float32",always_2d=True)
    if sr_a!=sr_b:
        g=gcd(sr_a,sr_b)
        a=resample_poly(a,sr_b//g,sr_a//g,axis=0)
    src=a.mean(axis=1);out=b.mean(axis=1)
    if len(src)<sr_b*5 or len(out)<sr_b*5:
        return {"used":False,"reason":"too_short"}
    if abs(len(src)-len(out))/sr_b>.15:
        return {"used":False,"reason":"time_drift"}
    n=min(len(src),len(out));hop=max(256,round(sr_b*.02))
    x,y=_frames(src[:n],hop),_frames(out[:n],hop)
    active=x>max(.003,float(np.percentile(x,85))*.25)
    stable=active&(y>.002)
    if stable.sum()<80:return {"used":False,"reason":"insufficient_voiced_frames"}
    relative=np.median(20*np.log10((x[stable]+1e-8)/(y[stable]+1e-8)))
    local=20*np.log10((x+1e-8)/(y+1e-8))-relative
    # Only boost preserved converted audio; no missing phoneme reconstruction.
    candidates=(active & (y>.002) & (local>7))
    # Smooth 80ms both directions to avoid resonant amplitude pumping.
    weight=gaussian_filter1d(candidates.astype(float),sigma=6.0)
    boost=np.clip((local-5)/13,0,1)
    boost=gaussian_filter1d(boost,sigma=6.0)
    gain_db=np.clip(2.6*np.minimum(boost,weight),0,2.6)
    for i in range(1,len(gain_db)):
        gain_db[i]=min(gain_db[i],gain_db[i-1]+0.11)
    for i in range(len(gain_db)-2,-1,-1):
        gain_db[i]=min(gain_db[i],gain_db[i+1]+0.11)
    gain=np.interp(np.arange(n),np.arange(len(gain_db))*hop,gain_db,left=0,right=0)
    corrected=out.copy();corrected[:n]=(out[:n]*np.power(10.0,gain/20.0)).astype("float32")
    peak=float(np.max(np.abs(corrected)))
    if peak>=.995:
        corrected*=.985/max(peak,1e-9)
    # Report remaining ratio using same relative-level reference as voice_guard.
    new_rms=_frames(corrected[:n],hop)
    before_drop=float(np.mean((local[active]<-1e9))) if not stable.any() else float(np.mean((local[active]>10)))
    new_local=20*np.log10((x+1e-8)/(new_rms+1e-8))-relative
    after_drop=float(np.mean(new_local[active]>10))
    gain_affected=int(np.count_nonzero(gain_db>.20))
    if gain_affected<5 or after_drop>before_drop+.005:
        return {"used":False,"reason":"no_safe_improvement",
                "before_weak_ratio":round(before_drop,4),
                "after_weak_ratio":round(after_drop,4)}
    sf.write(str(target),corrected,sr_b,subtype="FLOAT")
    return {"used":True,"method":"gentle_local_gain_only_no_splicing",
            "boost_ceiling_db":2.6,
            "max_applied_db":round(float(np.max(gain_db)),3),
            "affected_frames":gain_affected,
            "before_weak_ratio":round(before_drop,5),
            "after_weak_ratio":round(after_drop,5),
            "source_vocal_spliced":False,"pitch_modified":False,
            "waveform_clipping_prevented":peak>=.995}

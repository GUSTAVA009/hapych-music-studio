"""QA46 experimental soft continuity, leaving phonemes and F0 unchanged.
Attenuates dynamics pumping introduced by the older up-to-6.5dB rescue.
Isolated candidate only; NEVER replace production voice_continuity42.
"""
import numpy as np
import soundfile as sf
from scipy.ndimage import gaussian_filter1d
from scipy.signal import resample_poly
from math import gcd

def _rms(x, hop):
    v=np.asarray(x,dtype=np.float64)
    n=len(v)
    if n%hop:v=np.pad(v,(0,hop-n%hop))
    return np.sqrt(np.mean(v.reshape(-1,hop)**2,axis=1)+1e-12)

def repair(source,converted,target):
    a,sa=sf.read(str(source),dtype="float32",always_2d=True)
    b,sb=sf.read(str(converted),dtype="float32",always_2d=True)
    if sa!=sb:
        g=gcd(sa,sb);a=resample_poly(a,sb//g,sa//g,axis=0)
    src=a.mean(axis=1);out=b.mean(axis=1)
    if min(len(src),len(out))<sb*5:return {"used":False,"reason":"too_short"}
    if abs(len(src)-len(out))/sb>.15:return {"used":False,"reason":"time_drift"}
    n=min(len(src),len(out));hop=max(256,round(sb*.02))
    x,y=_rms(src[:n],hop),_rms(out[:n],hop)
    active=x>max(.003,float(np.percentile(x,85))*.25)
    stable=active&(y>.002)
    if stable.sum()<70:return {"used":False,"reason":"not_enough_voiced_audio"}
    delta=20*np.log10((x+1e-8)/(y+1e-8))
    relative=float(np.median(delta[stable]))
    local=delta-relative
    weak=active & (y>.002) & (local>8.5)
    # 20ms frames; 150ms smoothing prevents per-syllable pumping.
    smooth_activity=gaussian_filter1d(weak.astype(float),sigma=7.5,mode="constant")
    raw_boost=np.clip((local-6.5)*.46,0,3.0)*smooth_activity
    db=gaussian_filter1d(raw_boost,sigma=7.5,mode="constant")
    db=np.clip(db,0,2.6)
    # Slow gain changes (< 0.15 dB/20ms). Original transients remain audible.
    for j in range(1,len(db)):
        db[j]=min(db[j],db[j-1]+.15)
    for j in range(len(db)-2,-1,-1):
        db[j]=min(db[j],db[j+1]+.15)
    if np.max(db)<.15:return {"used":False,"reason":"no_significant_weak_regions"}
    positions=(np.arange(len(db))+.5)*hop
    gain=np.interp(np.arange(n),positions,db,left=0,right=0)
    correction=out.copy()
    correction[:n]=(out[:n]*(10**(gain/20))).astype(np.float32)
    peak=float(np.max(np.abs(correction)))
    if peak>.985:correction*=.985/peak
    new_local=20*np.log10((x+1e-8)/(_rms(correction[:n],hop)+1e-8))-relative
    before=float(np.mean(local[active]>10))
    after=float(np.mean(new_local[active]>10))
    # Do not allow quality regression just to produce a new version.
    if after>before+.003:return {"used":False,"reason":"weak_ratio_regression","before":before,"after":after}
    sf.write(str(target),correction,sb,subtype="FLOAT")
    return {"used":True,"method":"slow_phrase_gentle_gain_v46","gain_ceiling_db":2.6,
      "max_applied_db":round(float(np.max(db)),3),"max_step_db_per_20ms":.15,
      "gain_smoothing_ms":150,"affected_frames":int(np.sum(db>.12)),
      "before_weak_ratio":round(before,5),"after_weak_ratio":round(after,5),
      "phonemes_synthesized":False,"pitch_modified":False,
      "cross_singer_splicing":False,"peak_limited":peak>.985}

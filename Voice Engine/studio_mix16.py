"""Continuous vocal finishing: no gates, no phrase chopping and no pitch changes.
Bounded de-essing and measured vocal/backing balance. Reports are diagnostics,
not a subjective quality score. Originals remain unchanged.
"""
from __future__ import annotations
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfiltfilt,resample_poly
from scipy.ndimage import gaussian_filter1d,median_filter
from math import gcd

EPS=1e-10

def read_audio(path,sr=44100):
    x,rate=sf.read(str(path),dtype='float32',always_2d=True)
    if not np.all(np.isfinite(x)):raise ValueError('В аудио найдены некорректные отсчёты.')
    if rate!=sr:
        g=gcd(rate,sr);x=resample_poly(x,sr//g,rate//g,axis=0).astype('float32')
    return x

def frames_rms(x,hop):
    # Meter channel energy, not a mono sum that cancels out-of-phase material.
    a=np.asarray(x,dtype=np.float64)
    if a.ndim==1:a=a[:,None]
    if a.ndim!=2 or not len(a):raise ValueError("Empty or invalid audio for RMS")
    pad=(-len(a))%hop
    if pad:a=np.pad(a,((0,pad),(0,0)))
    return np.sqrt(np.mean(a.reshape(-1,hop,a.shape[1])**2,axis=(1,2))+EPS)

def db(x):return 20*np.log10(np.maximum(x,EPS))
def curve_frames(values,length,hop):
    return np.interp(np.arange(length),np.arange(len(values))*hop+hop/2,values).astype('float32')

def deess(x,sr):
    """Only attenuate a zero-phase 4.5..11 kHz band while it dominates.
    At most 6 dB, 10 ms frame analysis, smooth ~70 ms transitions.
    """
    if len(x)<sr//4:return x.copy(),{'max_reduction_db':0.0,'affected_fraction':0.0}
    band=sosfiltfilt(butter(3,[4500,min(11000,sr*.45)],btype='bandpass',fs=sr,output='sos'),x).astype('float32')
    hop=sr//100;total=frames_rms(x,hop);high=frames_rms(band,hop)
    ratio=high/np.maximum(total,EPS)
    excess=np.clip((ratio-.35)/.40,0,1)*np.clip((db(total)+48)/18,0,1)
    reduction=gaussian_filter1d(excess*6,1.6,mode='nearest')
    gain=curve_frames(10**(-reduction/20),len(x),hop)
    y=x+(gain-1)*band
    return y.astype('float32'),{'max_reduction_db':round(float(np.max(reduction)),2),
        'affected_fraction':round(float(np.mean(reduction>1)),4),'band_hz':[4500,min(11000,sr*.45)]}

def declick(x):
    """Repair only isolated 1-2 sample extreme impulses, never syllable gaps."""
    if len(x)<16:return x.copy(),0
    center=median_filter(x,size=5,mode='nearest')
    local=np.sqrt(np.maximum(gaussian_filter1d(x.astype('float64')**2,64),EPS))
    mask=(np.abs(x-center)>np.maximum(.13,6*local))
    edges=np.diff(np.r_[False,mask,False].astype('int8'));out=x.copy();n=0
    for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
        if b-a>2 or a==0 or b==len(x):continue
        out[a:b]=np.linspace(out[a-1],out[b],b-a+2)[1:-1];n+=b-a
    return out,n

def finish(vocal,backing,source_vocal,processed_path,mixed_path,sr=44100):
    v=read_audio(vocal,sr).mean(axis=1);b=read_audio(backing,sr);reference=read_audio(source_vocal,sr).mean(axis=1)
    n=len(b);drift=(len(v)-n)/sr
    if abs(drift)>.35:raise ValueError('Голосовая дорожка изменила длину на %.3f сек.; автосклейка отменена.'%drift)
    v=np.pad(v,(0,max(0,n-len(v))))[:n];reference=np.pad(reference,(0,max(0,n-len(reference))))[:n]
    v=v-np.mean(v);v,clicks=declick(v);v,sibilants=deess(v,sr)
    hop=sr//100;rv=frames_rms(v,hop);rr=frames_rms(reference,hop);rb=frames_rms(b,hop)
    active=rr>max(10**(-48/20),float(np.percentile(rr,85))*.15)
    active&=rv>10**(-55/20)
    if active.sum()<10:raise ValueError('Недостаточно слышимого вокала для безопасного баланса.')
    # Retain the generated singer's envelope, but keep the replacement audible.
    original_ratio=float(np.median(db(rr[active])-db(rb[active])))
    desired_ratio=float(np.clip(original_ratio,-8,-2))
    target_rr=rr*10**((desired_ratio-original_ratio)/20)
    ratios=db(target_rr)-db(rv)
    global_gain=float(np.clip(np.median(ratios[active]),-24,12))
    # 1.5-second smoothing; bounded movement; never close a gate on S/SH/CH.
    anchors=np.flatnonzero(active)
    levels=np.interp(np.arange(len(rv)),anchors,ratios[active])
    levels=gaussian_filter1d(levels,65,mode='nearest')
    levels=np.clip(levels,global_gain-3,global_gain+3)
    v*=curve_frames(10**(levels/20),n,hop)
    if b.shape[1]==1:b=np.repeat(b,2,axis=1)
    if b.shape[1]>2:b=b[:,:2]
    mixed=b+v[:,None]
    peak=float(np.max(np.abs(mixed)));attenuation=min(1,.94/max(peak,EPS))
    mixed*=attenuation
    sf.write(str(processed_path),v,sr,subtype='FLOAT')
    sf.write(str(mixed_path),mixed,sr,subtype='PCM_24')
    final_ratio=float(np.median(db(frames_rms(v,hop)[active])-db(rb[active])))
    return {'vocal_samples':n,'sample_rate':sr,'duration_seconds':n/sr,'original_length_drift_seconds':round(drift,5),
        'gate_used':False,'pitch_modified_by_mixer':False,'deesser':sibilants,'isolated_click_samples_repaired':clicks,
        'original_vocal_backing_db':round(original_ratio,2),'target_vocal_backing_db':round(desired_ratio,2),
        'result_vocal_backing_db':round(final_ratio,2),'vocal_global_gain_db':round(global_gain,2),
        'master_attenuation_db':round(float(db(attenuation)),2),'peak_dbfs':round(float(db(np.max(np.abs(mixed)))),2)}

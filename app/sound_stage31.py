"""Bounded SFX mixing v31.
Musically balanced level, fade envelopes, light spatial diffusion and side-chain
ducking. Does not alter pitch, duration or vocal timbre.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
SR=48000
DISTANT=("siren","police_radio","wind","room_laughter","crowd","radio_noise")
TRANSIENT=("click","coins","glass","cards","slap","knock","door","lighter","clock","beep","shutter","tap","tape")
LOW_END=("bass_impact","car_stereo","engine_start","engine_rev","engine_stop")
def rms(x):
    z=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(np.square(z))+1e-12))
def _active_rms(x):
    z=np.asarray(x,dtype=np.float64)
    if z.ndim==2:z=np.mean(z*z,axis=1)
    else:z=z*z
    hop=max(400,int(SR*.045))
    if len(z)<hop:return rms(x)
    frames=z[:len(z)//hop*hop].reshape(-1,hop).mean(axis=1)
    good=frames[frames>=np.percentile(frames,55)]
    return float(np.sqrt(np.mean(good)+1e-12)) if len(good) else rms(x)
def fade_seconds(name,length,ambient):
    if ambient:
        return min(1.5,length*.23),min(2.0,length*.28)
    if any(k in name for k in DISTANT):
        return min(.46,length*.21),min(.72,length*.24)
    if any(k in name for k in TRANSIENT):
        return min(.028,length*.13),min(.24,length*.29)
    return min(.075,length*.17),min(.36,length*.27)
def shape(chunk, music, name, ambient):
    """shape already-decoded stereo clip, return finished clip and metering dict"""
    chunk=np.ascontiguousarray(chunk,dtype=np.float32)
    n=len(chunk)
    length=n/SR
    fi,fo=fade_seconds(name,length,ambient)
    a=int(fi*SR);b=int(fo*SR)
    envelope=np.ones(n,dtype=np.float32)
    if a:envelope[:a]*=np.sin(np.linspace(0,np.pi/2,a,dtype=np.float32))**2
    if b:envelope[-b:]*=np.cos(np.linspace(0,np.pi/2,b,dtype=np.float32))**2
    # Dry sample is measured before fading, so long fades don't trigger gain inflation.
    active=_active_rms(chunk)
    backing=rms(music)
    if ambient:relative_db=-11.5;minimum=.006
    elif any(k in name for k in DISTANT):relative_db=-8.0;minimum=.010
    elif any(k in name for k in TRANSIENT):relative_db=-4.0;minimum=.018
    else:relative_db=-5.5;minimum=.014
    target=max(minimum,backing*10**(relative_db/20))
    peak=float(np.max(np.abs(chunk))) if n else 0.
    # RMS-based gain followed by a soft, bounded peak limiter: the previous
    # one-transient peak cap buried quiet effects with high crest factors.
    gain=float(min(10.,target/max(active,1e-8)))
    chunk*=gain
    soft_limited=float(np.max(np.abs(chunk)))>.70
    if soft_limited:
        chunk=(.72*np.tanh(chunk/.72)).astype(np.float32)
    chunk*=envelope[:,None]
    if ambient and n>SR//2:
        # One decorrelated quiet right reflection, while preserving mono compatibility.
        delay=min(int(.019*SR),n//6)
        if delay:
            dry=chunk[:,1].copy()
            chunk[delay:,1]=chunk[delay:,1]*.78+dry[:-delay]*.22
    audible=rms(chunk)
    return chunk,{
        "gain_db":round(float(20*np.log10(max(1e-9,gain))),2),
        "music_rms_dbfs":round(float(20*np.log10(max(backing,1e-9))),2),
        "effect_rms_dbfs":round(float(20*np.log10(max(audible,1e-9))),2),
        "target_relative_db":relative_db,
        "soft_peak_limited":soft_limited,
        "fade_in_s":round(fi,3),"fade_out_s":round(fo,3),
        "peak_dbfs":round(float(20*np.log10(max(1e-9,float(np.max(np.abs(chunk)))))),2)
    }
def finish(music, fx, duck):
    """Keep dry music mostly intact; gain-riding affects effects events only.
    Sparse early reflections live on FX bus, never on main vocals.
    """
    n=len(fx)
    # A quiet spatial tail is added to effects only.
    for left,right,ms,gain in ((0,1,54,.085),(1,0,91,.055)):
        shift=int(SR*ms/1000)
        if n>shift:
            fx[shift:,left]+=fx[:-shift,right]*gain
    # Clamp an overlapping FX bus softly, without clipping stacked events.
    maxfx=float(np.max(np.abs(fx)))
    if maxfx>.70:fx*=.70/maxfx
    if duck is not None:
        # Smooth 120 ms over control envelope; at most ~1.7 dB music reduction.
        hop=max(1,SR//100)
        smoothed=gaussian_filter1d(duck[::hop],sigma=5,mode="nearest")
        controls=np.repeat(smoothed,hop)[:n]
        music=music*(1-.18*np.clip(controls,0,1))[:,None]
    mixed=music+fx
    peak=float(np.max(np.abs(mixed)))
    gain=min(1.,.8912509381/max(peak,1e-9)) # -1 dBFS peak ceiling
    mixed*=gain
    return mixed.astype("float32"),{
        "ceiling_dbfs":-1.0,
        "master_attenuation_db":round(float(20*np.log10(max(1e-9,gain))),2),
        "fx_peak_before_limit":round(maxfx,4),
        "mono_compatible":True,
        "stereo_space":"subtle 19ms ambience decorrelation and 54/91ms low-level FX reflections",
        "max_duck_db":-1.7,
        "mixing_does_not_modify_pitch_or_vocal_phonemes":True
    }

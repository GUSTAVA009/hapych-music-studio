"""Studio vocal finishing v21: preserve consonants, stable stereo room.
No phoneme reconstruction, accent transformation, gate, hard autotune, or splice.
Retain direct lead vocal at center; low-level reflections create spatial depth.
"""
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfiltfilt
from scipy.ndimage import gaussian_filter1d
from studio_mix16 import read_audio,declick,db,EPS
from studio_mix20 import power_frames

def gentle_deess(signal,sr):
    """Restrained 1.8 dB peak reduction rather than old up-to-6 dB de-esser."""
    sig=np.asarray(signal,dtype=np.float32)
    upper=min(9800,sr*.44)
    if len(sig)<sr*.25 or upper<=4800:
        return sig.copy(),{"max_reduction_db":0,"affected_fraction":0}
    band=sosfiltfilt(butter(2,[4800,upper],btype="bandpass",fs=sr,output="sos"),sig).astype("float32")
    hop=max(250,round(sr*.012))
    total=power_frames(sig,hop)
    energy=power_frames(band,hop)
    ratio=energy/np.maximum(total,EPS)
    active=total>10**(-38/20)
    # Never suppress the whole high band: differentiate transient hiss peaks.
    amount=np.clip((ratio-.5)/.32,0,1)*active
    reduction_db=gaussian_filter1d(amount*1.8,3.2,mode="nearest")
    frame_positions=(np.arange(len(reduction_db))+.5)*hop
    gains=np.interp(np.arange(len(sig)),frame_positions,10**(-reduction_db/20),left=1,right=1).astype("float32")
    out=sig+(gains-1)*band
    return out.astype("float32"),{
        "max_reduction_db":round(float(np.max(reduction_db)),3),
        "affected_fraction":round(float(np.mean(reduction_db>.5)),4),
        "band_hz":[4800,round(upper)],
        "purpose":"protect consonant articulation; does not correct transcription or accent"}

def spatial_bed(b,sr):
    """Preserve low bass in the mid. Gently widen only existing side signal."""
    if b.shape[1]==1:b=np.repeat(b,2,axis=1)
    if b.shape[1]>2:b=b[:,:2]
    b=b.astype("float32",copy=True)
    mid=(b[:,0]+b[:,1])*.5
    side=(b[:,0]-b[:,1])*.5
    # Subbass unaffected: only widen side above 170 Hz.
    side_high=sosfiltfilt(butter(2,170,btype="highpass",fs=sr,output="sos"),side).astype("float32")
    side=side+side_high*.18
    b[:,0]=mid+side
    b[:,1]=mid-side
    return b

def vocal_room(v,sr):
    """Diffuse early stereo reflections; the dry lead stays dead center."""
    band=sosfiltfilt(butter(2,[250,6500],btype="bandpass",fs=sr,output="sos"),v).astype("float32")
    stereo=np.repeat(v[:,None],2,axis=1)
    for channel,delay_ms,level in ((0,17,.065),(1,31,.070),(0,47,.035),(1,64,.035)):
        n=max(1,int(sr*delay_ms/1000))
        stereo[n:,channel]+=band[:-n]*level
    return stereo

def finish(vocal,backing,source_vocal,processed_path,mixed_path,sr=44100,chorus_ranges=None):
    v=read_audio(vocal,sr).mean(axis=1)
    b=read_audio(backing,sr)
    reference=read_audio(source_vocal,sr)
    n=len(b)
    drift=(len(v)-n)/sr
    if abs(drift)>.35:raise ValueError("Converted vocal length mismatch (%.3f s)"%drift)
    v=np.pad(v,(0,max(0,n-len(v))))[:n]
    reference=np.pad(reference,((0,max(0,n-len(reference))),(0,0)))[:n]
    v=v-np.mean(v)
    v,clicks=declick(v)
    v,deess=gentle_deess(v,sr)
    hop=max(250,sr//100)
    rr=power_frames(reference,hop)
    rv=power_frames(v,hop)
    rb=power_frames(b,hop)
    active=(rr>max(10**(-48/20),float(np.percentile(rr,85))*.15))&(rv>10**(-55/20))
    if active.sum()<10:raise ValueError("Not enough measurable converted vocals")
    gain_db=float(np.clip(np.median(db(rr[active])-db(rv[active])),-24,18))
    v*=10**(gain_db/20)
    b=spatial_bed(b,sr)
    from pathlib import Path
    import sys
    app_path=str(Path(__file__).resolve().parent.parent/"app")
    if app_path not in sys.path:sys.path.insert(0,app_path)
    from chorus_layers34 import vocal_double
    doubles,backing_report=vocal_double(v,sr,chorus_ranges or [])
    mixed=b+vocal_room(v,sr)+doubles
    peak=float(np.max(np.abs(mixed)))
    attenuation=min(1,.8912509381/max(peak,EPS))
    sf.write(str(processed_path),v,sr,subtype="FLOAT")
    sf.write(str(mixed_path),mixed*attenuation,sr,subtype="PCM_24")
    return {
        "method":"source_level_constant_gain_spacious21",
        "gain_db":round(gain_db,3),
        "dynamic_gain_used":False,"gate_used":False,"pitch_modified_by_mixer":False,
        "source_vocal_blended":False,
        "backing_doubles":backing_report,
        "source_vocal_backing_db":round(float(np.median(db(rr[active])-db(rb[active]))),2),
        "result_vocal_backing_db":round(float(np.median(db(power_frames(v,hop)[active])-db(rb[active]))),2),
        "deesser":deess,"clicks_repaired":clicks,
        "stereo_depth":"direct center lead, low-level asymmetric early reflections 17-64ms",
        "backing_stereo_width":1.18,"subbass_is_mono_safe":True,
        "master_gain_db":round(float(db(attenuation)),2),
        "peak_dbfs":round(float(db(max(peak*attenuation,EPS))),2),
        "acoustic_quality_verified":False,
        "phoneme_reconstruction_performed":False,
        "pronunciation_or_accent_corrected":False,
    }

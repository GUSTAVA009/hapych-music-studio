"""Music Studio 34 - non-destructive end-to-end master finishing.
Fades/short silence handles fixed-duration ACE-Step hard edges. Does not claim
that a harmonic cadence or natural ending has been composed by the model.
"""
from pathlib import Path
from math import gcd
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

def inspect_audio(path):
    info=sf.info(str(path))
    if info.frames < info.samplerate*2:
        raise ValueError("Master audio too short to shape")
    with sf.SoundFile(str(path)) as f:
        n=min(info.samplerate//2,info.frames)
        first=f.read(n,dtype="float32",always_2d=True)
        f.seek(info.frames-n);last=f.read(n,dtype="float32",always_2d=True)
    def meter(a):
        return round(float(20*np.log10(max(1e-9,np.sqrt(np.mean(a.astype("float64")**2))))),2)
    return {"duration_s":info.duration,"samplerate":info.samplerate,"channels":info.channels,
            "first_half_second_rms_dbfs":meter(first),
            "last_half_second_rms_dbfs":meter(last)}

def finish(source,destination=None,fade_in_s=None,fade_out_s=None,head_s=.10,tail_s=.55,chorus_ranges=None):
    source=Path(source)
    info=sf.info(str(source))
    if info.duration<2 or info.duration>610:raise ValueError("Unexpected master duration")
    sr=info.samplerate
    audio,sr=sf.read(str(source),dtype="float32",always_2d=True)
    if audio.shape[1]>2: audio=audio[:,:2]
    if audio.shape[1]==1:audio=np.repeat(audio,2,axis=1)
    if not np.all(np.isfinite(audio)):raise ValueError("Master contains invalid audio")
    from chorus_layers34 import chorus_stereo_space
    audio, chorus_info=chorus_stereo_space(audio,sr,chorus_ranges)
    n=len(audio)
    duration=n/sr
    fi=min(2.4,max(.45,duration*.038)) if fade_in_s is None else float(fade_in_s)
    fo=min(4.2,max(1.1,duration*.088)) if fade_out_s is None else float(fade_out_s)
    if fi+fo>duration*.45:
        scale=duration*.45/(fi+fo);fi*=scale;fo*=scale
    a=int(round(fi*sr));b=int(round(fo*sr))
    # Half-cosine fades have zero end slope and do not create audible clicks.
    if a:
        fade=.5-.5*np.cos(np.linspace(0,np.pi,a,dtype=np.float32))
        audio[:a]*=fade[:,None]
    if b:
        fade=.5+.5*np.cos(np.linspace(0,np.pi,b,dtype=np.float32))
        audio[-b:]*=fade[:,None]
    peak=float(np.max(np.abs(audio)))
    attenuation=min(1.,.891250938/max(1e-10,peak))
    audio*=attenuation
    start_pad=np.zeros((int(round(head_s*sr)),2),dtype=np.float32)
    end_pad=np.zeros((int(round(tail_s*sr)),2),dtype=np.float32)
    audio=np.concatenate((start_pad,audio,end_pad),axis=0)
    if destination is None:
        destination=source
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Temp WAV written before replacing a source. Never write partial masters.
    tmp=destination.with_name(destination.stem+".finish34.part.wav")
    try:
        sf.write(str(tmp),audio,sr,subtype="PCM_24")
        if tmp.stat().st_size<10000:raise RuntimeError("Incomplete master")
        tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)
    return {
        "revision":"studio_finisher34_v1",
        "source_duration_seconds":round(duration,4),
        "finished_duration_seconds":round(len(audio)/sr,4),
        "fade_in_seconds":round(fi,3),"fade_out_seconds":round(fo,3),
        "head_silence_seconds":head_s,"tail_silence_seconds":tail_s,
        "attenuation_db":round(float(20*np.log10(max(attenuation,1e-9))),3),
        "chorus_spatial_processing":chorus_info,
        "peak_dbfs":round(float(20*np.log10(max(1e-9,peak*attenuation))),3),
        "edge_qa":inspect_audio(destination),
        "musical_cadence_verified":False,
        "vocal_phrase_completion_verified":False,
        "original_was_preserved_when_exported_to_new_master":str(source.resolve())!=str(destination.resolve()),
    }

"""Section-aware studio chorus processing. Doubles are NOT new singers.
Lead remains dry and centered. Stereo accents are subtle filtered copies only
of one authorized vocal, not cloned/third-party profiles.
"""
import re
import numpy as np
from scipy.signal import butter,sosfiltfilt

def chorus_windows(sections,lrc,duration):
    from sound_effects29 import _sections_from_lrc
    if not sections:return [],"no_sections"
    bounds,aligned=_sections_from_lrc(sections,lrc,duration)
    windows=[]
    for i,section in enumerate(sections):
        name=str(section.get("section",""))
        if re.search(r"\bchorus\b|\bhook\b|\brefrain\b|припев",name,re.I):
            start,end=max(0,float(bounds[i])),min(duration,float(bounds[i+1]))
            if end-start>1:windows.append([round(start,3),round(end,3)])
    return windows,"lrc_aligned_estimate" if aligned else "section_proportional_estimate"

def mask(n,sr,windows,attack=.3,release=.6):
    env=np.zeros(n,dtype=np.float32)
    a=int(attack*sr);b=int(release*sr)
    for start,end in windows or []:
        left=max(0,min(n,int(start*sr)));right=max(left,min(n,int(end*sr)))
        if right-left<sr*.25:continue
        e=np.ones(right-left,dtype=np.float32)
        f=min(a,len(e)//3);g=min(b,len(e)//3)
        if f:e[:f]=np.linspace(0,1,f,dtype=np.float32)
        if g:e[-g:]=np.linspace(1,0,g,dtype=np.float32)
        env[left:right]=np.maximum(env[left:right],e)
    return env

def vocal_double(v,sr,choruses):
    """Very quiet stereo doubles for choruses from the same dry vocal."""
    n=len(v);result=np.zeros((n,2),np.float32)
    if not choruses:return result,{"applied":False,"layers":0,"reason":"No chorus tags provided"}
    envelope=mask(n,sr,choruses)
    if not np.any(envelope):return result,{"applied":False,"layers":0,"reason":"No valid chorus time ranges"}
    filtered=sosfiltfilt(butter(2,[240,min(4800,sr*.43)],btype="bandpass",fs=sr,output="sos"),v).astype(np.float32)
    delays=[(0,.027,.108),(1,.043,.087),(0,.057,.051),(1,.068,.045)]
    for channel,delay,volume in delays:
        shift=int(sr*delay)
        if n>shift:result[shift:,channel]+=filtered[:-shift]*volume
    result*=envelope[:,None]
    return result,{"applied":True,"layers":4,"kind":"two panned pairs of filtered low-gain doubles",
                   "independent_singers":False,
                   "pitch_shifting":False,"source_speaker":"the same selected vocal",
                   "chorus_regions":len(choruses),"max_nominal_gain_db":-19.3,
                   "audible_quality_verified":False}

def chorus_stereo_space(audio,sr,windows,depth=.13):
    """Gentle chorus-only stereo diffusion; no bass width processing."""
    if not windows:return audio,{"applied":False,"reason":"No chorus sections"}
    n=len(audio);envelope=mask(n,sr,windows)
    if not np.any(envelope):return audio,{"applied":False,"reason":"No timed regions"}
    audio=audio.copy()
    mid=(audio[:,0]+audio[:,1])*.5
    side=(audio[:,0]-audio[:,1])*.5
    side_high=sosfiltfilt(butter(2,210,btype="highpass",fs=sr,output="sos"),side).astype("float32")
    audio[:,0]+=side_high*depth*envelope
    audio[:,1]-=side_high*depth*envelope
    return audio,{"applied":True,"section_count":len(windows),"side_enhancement":depth,
                  "subbass_unmodified":True,"independent_backing_singers":False}

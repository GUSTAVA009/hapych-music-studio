"""Pitch micro-correction for singing F0 contours before timbre synthesis.
Operates only on voiced frames and avoids strong note snapping.
"""
import numpy as np
from scipy.ndimage import median_filter, gaussian_filter1d

def stabilize_f0(f0, strength=0.18):
    data=np.asarray(f0,dtype=np.float32).copy()
    strength=float(np.clip(strength,0.,0.65))
    if strength<=0 or data.size<16:
        return data
    valid=np.isfinite(data)&(data>60)&(data<1250)
    pad=np.r_[False,valid,False].astype(np.int8)
    starts=np.flatnonzero(np.diff(pad)==1)
    ends=np.flatnonzero(np.diff(pad)==-1)
    for a,b in zip(starts,ends):
        if b-a<15: # under 150ms, skip consonants and brief voiced sounds
            continue
        segment=data[a:b]
        midi=69+12*np.log2(segment/440)
        center=median_filter(midi,size=5,mode="nearest")
        gliss=np.abs(np.gradient(center)) > 0.09
        correction=np.clip(np.rint(center)-center,-0.30,0.30)
        correction[gliss]=0
        correction=gaussian_filter1d(correction,sigma=3,mode="nearest")
        # Softer than hard autotune; retain expressive human vibrato and slides.
        adjusted=0.88*midi+0.12*center+strength*correction
        data[a:b]=440*np.power(2.,(adjusted-69)/12)
    return data.astype(np.float32)

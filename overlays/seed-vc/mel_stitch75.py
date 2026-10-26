"""QA75 experimental acoustic-aware overlap of diffusion-predicted log-mels.

Instead of always blending two independently predicted mel streams for ~1.5s
through live singing, find a real low-energy source-vocal region and switch
there with a short complementary overlap ramp. This module is diagnostic only.
"""
from __future__ import annotations
import numpy as np
import torch
from scipy.ndimage import uniform_filter1d

def source_energy(wave, hop=512, total=None):
    a=np.asarray(wave,dtype=np.float32).ravel()
    if total is None: total=(len(a)+hop-1)//hop
    if len(a)<total*hop: a=np.pad(a,(0,total*hop-len(a)))
    a=a[:total*hop].reshape(total,hop)
    e=np.sqrt(np.mean(a.astype(np.float64)**2,axis=1)+1.e-11)
    return uniform_filter1d(e,size=9,mode='nearest').astype(np.float32)

def plan(energy, max_window, overlap, *, hop=512, sr=44100,
         lookback_seconds=3.0, min_quiet_seconds=.20):
    """Return non-overwriting audio frame intervals and evidence for transitions.

    The center of each crossfade lies inside a *measured* quiet region; if
    none exists, use unchanged default full-overlap crossfading. Min segment
    length guards against producing many short CFM calls.
    """
    rms=np.asarray(energy,dtype=np.float32).ravel()
    if not np.isfinite(rms).all(): raise ValueError('Non-finite source energy')
    total=len(rms)
    assert 0<overlap*3<max_window and total>0
    threshold=max(.002,float(np.percentile(rms,85))*.15)
    quiet=rms<threshold
    minimum=max(8,round(min_quiet_seconds*sr/hop))
    candidates=(uniform_filter1d(quiet.astype(np.float32),size=minimum,mode='constant')>=.999)
    segments=[]; transitions=[]; start=0
    max_lag=round(lookback_seconds*sr/hop)
    while start<total:
        max_end=min(total,start+max_window)
        if max_end==total:
            segments.append((start,total))
            break
        default_center=max_end-overlap//2
        lo=max(start+round(4*sr/hop),default_center-max_lag)
        hi=default_center-2
        valid=np.flatnonzero(candidates[lo:hi+1])+lo if hi>=lo else np.empty(0,dtype=int)
        if len(valid):
            center=int(valid[-1])
            end=min(max_end,center+overlap//2)
            fade=max(10,min(20,minimum))
            kind='quiet'
        else:
            center=int(default_center)
            end=int(max_end)
            fade=int(overlap)
            kind='default'
        if not (start+overlap*2<end<=max_end):
            center=int(default_center);end=int(max_end)
            fade=int(overlap);kind='default'
        new_start=end-overlap
        if new_start<=start: raise RuntimeError('No forward progress in mel splitting')
        segments.append((start,end))
        transitions.append({'center':center,'end':end,'next_start':new_start,
            'fade_frames':fade,'kind':kind,'source_rms':float(rms[center]),
            'source_rms_threshold':threshold,'time_s':round(center*hop/sr,3)})
        start=new_start
        if len(segments)>40: raise RuntimeError('Too many segments')
    assert segments[0][0]==0 and segments[-1][1]==total
    assert all(segments[i][1]-segments[i+1][0]==overlap for i in range(len(segments)-1))
    assert len(transitions)==len(segments)-1
    return segments,transitions

def _rise(frames,center,fade):
    vals=(frames-(center-fade/2))/max(1,fade)
    vals=np.clip(vals,0,1)
    # raised cosine, C1 continuous even through note release
    return .5-.5*np.cos(np.pi*vals)

def accumulate(canvas,weights,part,start,end,index,transitions):
    if part.ndim!=3 or end<=start:raise ValueError('Invalid mel shapes')
    length=end-start
    if part.shape[-1]!=length:raise ValueError('Unexpected mel frames')
    indices=np.arange(start,end)
    w=np.ones(length,dtype=np.float32)
    if index>0:
        t=transitions[index-1]
        w*=_rise(indices,t['center'],t['fade_frames']).astype(np.float32)
    if index<len(transitions):
        t=transitions[index]
        w*=(1.-_rise(indices,t['center'],t['fade_frames'])).astype(np.float32)
    # Explicit all-zero regions are supported as other neighboring chunk
    # covers the same frames. Never divide by an uncovered frame.
    w_cpu=torch.from_numpy(w)
    part_cpu=part.detach().float().cpu()
    canvas[...,start:end]+=part_cpu*w_cpu
    weights[start:end]+=w_cpu

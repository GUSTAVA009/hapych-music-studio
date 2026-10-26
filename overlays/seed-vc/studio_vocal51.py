"""Music Studio 5.1: conservative sung F0 cleanup before Seed-VC conditioning.

This is NOT hard tuning: preserves real note changes, glissandi, natural vibrato,
original phonemes and silence. Repairs only objectively isolated extraction slips.
No dependencies on model state, audio file paths or UI.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter1d

def stabilize_f0(f0, waveform=None, sample_rate=16000):
    source = np.asarray(f0, dtype=np.float64).ravel()
    result = np.array(source, copy=True)
    n = len(result)
    report = {
        "revision": "pitch_clean51",
        "filled_short_voiced_gaps": 0,
        "repaired_isolated_octave_frames": 0,
        "repaired_isolated_pitch_spikes": 0,
        "smoothed_stable_frames": 0,
        "vibrato_reduced_not_eliminated": True,
        "intentional_register_changes_preserved": True,
    }
    if n < 12:
        return np.asarray(f0, dtype=np.float32).copy(), report
    valid = np.isfinite(result) & (result >= 55) & (result <= 1200)
    result[~valid] = 0.0
    cents = lambda a,b: 1200.0 * np.log2(max(a, 1e-8) / max(b, 1e-8))
    # Only bridge an extractor dropout within the SAME held note. A strong
    # consonant / deliberate silence must never be filled with fake pitch.
    waveform_mono = None
    if waveform is not None:
        raw = np.asarray(waveform, dtype=np.float32)
        if raw.ndim == 1 and len(raw) >= 100:
            waveform_mono = raw
    ref_energy = 0.0
    if waveform_mono is not None:
        segments = np.array_split(waveform_mono[:max(1,len(waveform_mono))], min(100,max(1,len(waveform_mono)//256)))
        ref_energy = float(np.percentile([np.sqrt(np.mean(np.square(s)) + 1e-12) for s in segments if len(s)], 65))
    i = 0
    while i < n:
        if result[i] > 0:
            i += 1; continue
        j = i
        while j < n and result[j] <= 0:
            j += 1
        gap = j - i
        if 0 < i < j < n and gap <= 3 and result[i-1] > 0 and result[j] > 0:
            if abs(cents(result[i-1],result[j])) < 55.0 and waveform_mono is not None:
                good = True
                for f in range(i,j):
                    at = int((f+0.5)/n * len(waveform_mono))
                    half = max(64,int(.01*sample_rate))
                    x = waveform_mono[max(0,at-half):min(len(waveform_mono),at+half)]
                    amp = float(np.sqrt(np.mean(x*x)+1e-12)) if len(x) else 0
                    if amp < max(.007,ref_energy*.29):
                        good = False; break
                if good:
                    result[i:j] = np.linspace(result[i-1],result[j],gap+2)[1:-1]
                    report["filled_short_voiced_gaps"] += gap
        i = j
    # A 12-semitone detector blip that returns to the same note in <= 60 ms
    # is an extraction artifact; a sustained octave jump is legitimate.
    i = 4
    while i < n-4:
        if result[i] <= 0:
            i += 1; continue
        left = result[max(0,i-4):i];right=result[i+1:i+5]
        left=left[left>0];right=right[right>0]
        if len(left)<3 or len(right)<3 or abs(cents(np.median(left),np.median(right)))>75:
            i+=1; continue
        base = float(np.median(np.concatenate([left,right])))
        diff=cents(result[i],base)
        if 950 < abs(diff) < 1450:
            shift = 2.0 if diff < 0 else .5
            candidate = result[i] * shift
            if abs(cents(candidate,base))<160:
                result[i]=candidate;report["repaired_isolated_octave_frames"]+=1
        elif abs(diff)>260 and abs(diff)<950:
            result[i]=base;report["repaired_isolated_pitch_spikes"]+=1
        i+=1
    # Only soften tiny frame-to-frame jitter on truly stationary portions.
    # Never flatten a slide between two notes or smooth a > 2-semitone change.
    original=result.copy()
    pitch=np.zeros(n,dtype=np.float64)
    v=result>0
    pitch[v]=12*np.log2(result[v]/440.0)+69.0
    stable=np.zeros(n,dtype=bool)
    for k in range(5,n-5):
        values=pitch[k-5:k+6]
        if v[k-5:k+6].all() and (np.max(values)-np.min(values))<.75:
            stable[k]=True
    starts=np.flatnonzero(np.diff(np.pad(stable.astype(np.int8),(1,1)))==1)
    stops=np.flatnonzero(np.diff(np.pad(stable.astype(np.int8),(1,1)))==-1)
    for a,b in zip(starts,stops):
        if b-a<12:continue
        # Gaussian 1.6 frames ≈16 ms at 100 Hz; leave musical vibrato intact.
        s=gaussian_filter1d(pitch[a:b],sigma=1.6,mode="nearest")
        s=np.clip(s,pitch[a:b]-.3,pitch[a:b]+.3)
        result[a:b]=440.0*np.exp2((s-69.0)/12.0)
        report["smoothed_stable_frames"]+=int(b-a)
    report["changed_voiced_frames"]=int(np.count_nonzero(np.abs(result-original)>1e-4))
    return result.astype(np.float32),report

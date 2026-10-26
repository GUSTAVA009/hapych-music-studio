"""Conservative register control for Music Studio; no chromatic auto-tune.
An octave move preserves note classes. A free median-frequency shift does not.
"""
import numpy as np
from scipy.ndimage import median_filter

def pitch_stats(f0):
    f=np.asarray(f0,dtype=np.float64)
    valid=np.isfinite(f)&(f>=55)&(f<=900)
    x=f[valid]
    if len(x)<20:
        return {'voiced_frames':int(len(x)),'reliable':False}
    q=np.percentile(x,[15,50,85])
    return {'voiced_frames':int(len(x)),'reliable':True,
            'p15_hz':round(float(q[0]),3),'median_hz':round(float(q[1]),3),
            'p85_hz':round(float(q[2]),3)}

def repair_brief_octave_errors(f0):
    """Correct only isolated 10..50ms octave outliers, not vibrato or glides."""
    data=np.asarray(f0,dtype=np.float32).copy()
    valid=np.isfinite(data)&(data>=55)&(data<900)
    midi=69+12*np.log2(np.maximum(data,1)/440.)
    center=median_filter(midi,size=9,mode='nearest')
    delta=midi-center
    suspect=valid&(np.abs(delta)>10.5)&(np.abs(delta)<13.5)
    cuts=np.diff(np.r_[False,suspect,False].astype(np.int8))
    fixed=0
    for a,b in zip(np.flatnonzero(cuts==1),np.flatnonzero(cuts==-1)):
        if b-a>5 or a==0 or b>=len(data) or not valid[a-1] or not valid[b]: continue
        if abs(float(midi[a-1]-midi[b]))>2: continue
        direction=1 if float(np.median(delta[a:b]))>0 else -1
        data[a:b]*=2.**(-direction)
        fixed+=b-a
    return data,fixed

def adapt_register(source_f0, reference_f0, mode='auto'):
    if mode not in ('auto','original','lower'):
        raise ValueError('Unknown register mode')
    source=np.asarray(source_f0,dtype=np.float32)
    ref=pitch_stats(reference_f0)
    src=pitch_stats(source)
    out,fixed=repair_brief_octave_errors(source) if mode!='original' else (source.copy(),0)
    semitones=0
    reason='keep_melody'
    if mode=='lower':
        semitones=-12; reason='user_lower_octave'
    elif mode=='auto' and src['reliable'] and ref['reliable']:
        ratio=src['median_hz']/ref['median_hz']
        high=src['p85_hz']/ref['p85_hz']
        # Speech does not reveal a singer's full range; only move an octave
        # when both central pitch and upper register are clearly mismatched.
        if (ratio>=1.75 and high>=1.8) or (ratio>=1.5 and high>=1.9):
            if src['p15_hz']/2>=48 and src['median_hz']/2>=58:
                semitones=-12; reason='upper_register_far_above_reference'
    phrase_moves=[]
    if semitones:
        mask=np.isfinite(out)&(out>1)
        out[mask]*=2.**(semitones/12.)
    elif mode=='auto' and ref['reliable']:
        # If a song includes both low and high phrases, do not move the entire
        # melody below the usable register. Move only clearly high phrases.
        voiced=np.isfinite(out)&(out>=55)&(out<900)
        # Bridge short unvoiced consonants for grouping only. Never introduce
        # F0 into silence, and never change octave independently for each word.
        grouped=voiced.copy()
        gaps=np.diff(np.r_[True,voiced,True].astype(np.int8))
        for a,b in zip(np.flatnonzero(gaps==-1),np.flatnonzero(gaps==1)):
            if a>0 and b<len(out) and b-a<=18: grouped[a:b]=True
        edges=np.diff(np.r_[False,grouped,False].astype(np.int8))
        for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
            values=out[a:b][voiced[a:b]]
            if b-a<60 or len(values)<30: continue
            low,mid,high=np.percentile(values,[10,50,85])
            if low>=104 and mid/ref['median_hz']>=1.7 and high/ref['p85_hz']>=1.75:
                section=out[a:b]
                section[voiced[a:b]]*=0.5
                phrase_moves.append({'start_frame':int(a),'end_frame':int(b),'semitones':-12})
        if phrase_moves: reason='high_voiced_phrases_lowered_one_octave'
    report={'mode':mode,'source':src,'reference':ref,'applied_semitones':semitones,
            'phrase_octave_moves':phrase_moves,
            'brief_octave_frames_repaired':int(fixed),'reason':reason,'conditioned':pitch_stats(out)}
    return out,report

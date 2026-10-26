"""One register decision per song, never per word or phrase."""
import numpy as np
from studio_identity import pitch_stats, repair_brief_octave_errors

def adapt_register(source_f0,reference_f0,mode='auto'):
    if mode not in ('auto','original','lower'):raise ValueError('Unknown register mode')
    source=np.asarray(source_f0,dtype=np.float32)
    out,fixed=repair_brief_octave_errors(source) if mode!='original' else (source.copy(),0)
    src=pitch_stats(source);ref=pitch_stats(reference_f0)
    semitones=-12 if mode=='lower' else 0;reason='manual_octave' if semitones else 'continuous_original_melody'
    if mode=='auto' and src['reliable'] and ref['reliable']:
        # A spoken sample does not prove a singing range. Only a uniformly high
        # source may move by one complete octave, with no within-song switches.
        if src['median_hz']/ref['median_hz']>=1.95 and src['p15_hz']>=125:
            semitones=-12;reason='whole_song_octave_to_reference_range'
    voiced=np.isfinite(out)&(out>1)
    if semitones:out[voiced]*=2**(semitones/12)
    return out,{'mode':mode,'source':src,'reference':ref,'applied_semitones':semitones,
                'phrase_octave_moves':[],'brief_octave_frames_repaired':int(fixed),
                'reason':reason,'conditioned':pitch_stats(out),'version':'1.6'}

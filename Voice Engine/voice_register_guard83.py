"""QA83 register guard: report gross pitch-register mismatches, do not infer gender.

Comparing singing F0 against a speech reference is heuristic; this only flags
review conditions. It NEVER retunes a song or treats spoken F0 as a strict limit.
"""
from __future__ import annotations
import math

def evaluate(register_report):
    r=dict(register_report or {})
    source=dict(r.get('source') or {})
    ref=dict(r.get('reference') or {})
    actual=dict(r.get('output_actual') or {})
    med_source=source.get('median_hz')
    med_ref=ref.get('median_hz')
    med_output=actual.get('median_hz')
    result={'status':'unknown','review_required':False,
        'reliable':False,'reason':'Pitch-range comparison was not available',
        'output_pitch_not_audio_quality_certificate':True}
    try:
        a,b,c=float(med_source),float(med_ref),float(med_output)
    except (ValueError,TypeError):
        return result
    if not all(math.isfinite(x) for x in (a,b,c)) or min(a,b,c)<55:
        return result
    reliable=bool(source.get('reliable') and ref.get('reliable') and actual.get('reliable'))
    ratio=c/b
    result.update(source_median_hz=round(a,1),reference_median_hz=round(b,1),
         actual_output_median_hz=round(c,1),
         output_over_reference_ratio=round(ratio,3),reliable=reliable)
    if not reliable:
        result['status']='insufficient_data'
        return result
    if r.get('mode')=='original' and ratio>=1.75 and a/b>=1.75 and c>180 and 65<=b<=170:
        result.update(status='review_high_register',review_required=True,
         reason=('Generated singing remains in a much higher register than the '
          'selected reference. This may be intentional singing, but the track '
          'must not be automatically certified as that recorded vocal range.'))
    else:
        result.update(status='no_large_mismatch_detected',reason='No gross same-song pitch-range mismatch detected; naturalness/identity still unverified')
    return result

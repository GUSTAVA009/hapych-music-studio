"""QA100: lightweight sub-semitone intonation audit for singing converters.

The existing safety gate rejected only major multi-semitone shifts, so a
song with repeated 30-70-cent deviations could be marked 'passed'. This
detects drift objectively without changing audio, F0, speaker identity or
user voice recordings. It cannot judge artistic expression/blue notes.
"""
import numpy as np

def measure(conditioned_f0,converted_f0):
    a=np.asarray(conditioned_f0,dtype=np.float64).ravel()
    b=np.asarray(converted_f0,dtype=np.float64).ravel()
    n=min(len(a),len(b))
    a=a[:n];b=b[:n]
    voiced=(np.isfinite(a)&np.isfinite(b)&(a>=55)&(a<=1100)&(b>=55)&(b<=1100))
    status={'status':'not_proven','reliable':False,
      'matched_voiced_frames':int(voiced.sum()),
      'report_only':True,'note_corrected':False,
      'meaning':'Pitch extraction is an estimate; no speaker identity or naturalness certification.'}
    if voiced.sum()<150:return status
    midi_a=np.zeros(n,dtype=np.float64);midi_b=np.zeros(n,dtype=np.float64)
    midi_a[voiced]=69+12*np.log2(a[voiced]/440)
    midi_b[voiced]=69+12*np.log2(b[voiced]/440)
    cents=np.abs(100*(midi_b[voiced]-midi_a[voiced]))
    # Small glides and ornamentation are valid; report rather than hard snap.
    stable=voiced & (np.abs(np.diff(midi_a,prepend=midi_a[0]))<.28)
    if stable.sum()>150:
        cents_stable=np.abs(100*(midi_b[stable]-midi_a[stable]))
    else:cents_stable=cents
    p50=float(np.percentile(cents,50));p90=float(np.percentile(cents,90))
    p90stable=float(np.percentile(cents_stable,90))
    # The frame-level stat is a diagnostic: warn only, never modify melody.
    suspicious=(p90>=42.0 and np.mean(cents>35)>=.13)
    status.update(status='review' if suspicious else 'not_flagged',
        reliable=True,matched_voiced_frames=int(voiced.sum()),
        stable_source_frames=int(stable.sum()),
        p50_abs_pitch_error_cents=round(p50,2),
        p90_abs_pitch_error_cents=round(p90,2),
        stable_note_p90_abs_error_cents=round(p90stable,2),
        fraction_frames_over_35_cents=round(float(np.mean(cents>35)),4),
        fraction_frames_over_70_cents=round(float(np.mean(cents>70)),4),
        meaning=('Вокал сохраняет общий регистр, но на отдельных нотах '
                 'отклоняется от исходной мелодии. Возможна слышимая фальшь; '
                 'результат требует прослушивания.' if suspicious else
                 'Крупная локальная неточность высоты не выявлена; '
                 'естественность и тембр не подтверждены.'),
        broad_pitch_range_control_only=False,
        audible_falseness_not_proven_by_metric_alone=True)
    return status

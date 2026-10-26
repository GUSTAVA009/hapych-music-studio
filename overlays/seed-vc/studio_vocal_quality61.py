"""Non-destructive vocal melody integrity screening.
Compare *aligned windows* of requested F0 and synthesized F0.
A pass is not proof of natural voice or pronunciation.
"""
import numpy as np


def _valid(x):
    a = np.asarray(x, dtype=np.float64).ravel()
    return a[np.isfinite(a) & (a >= 55) & (a <= 1200)]


def evaluate_pairs(pairs):
    reports = []
    severe = 0
    for window in pairs:
        expected = np.asarray(window["expected"], dtype=float).ravel()
        actual = np.asarray(window["actual"], dtype=float).ravel()
        e, a = _valid(expected), _valid(actual)
        e_count, a_count = len(e), len(a)
        e_fraction = e_count / max(1, len(expected))
        a_fraction = a_count / max(1, len(actual))
        e_ok = e_count >= 100 and e_fraction >= 0.12
        a_ok = a_count >= 80 and a_fraction >= 0.10
        shift = (float(12.0 * np.log2(np.median(a) / np.median(e)))
                 if e_ok and a_ok else None)
        issue = None
        if e_ok and a_count < max(20, e_count * 0.08):
            issue = "strong_voicing_loss"
        elif (shift is not None and abs(shift) >= 4.0
              and e_count >= 300 and a_count >= 240):
            # A multi-semitone systematic shift is never acceptable unless
            # explicitly requested in expected F0, even for a short song.
            issue = "large_unrequested_pitch_shift"
        if issue:
            severe += 1
        reports.append({
            "start_s": round(float(window["start_s"]), 2),
            "expected_voiced_frames": e_count,
            "actual_voiced_frames": a_count,
            "expected_voiced_fraction": round(e_fraction, 3),
            "actual_voiced_fraction": round(a_fraction, 3),
            "median_shift_semitones": round(shift, 2) if shift is not None else None,
            "issue": issue,
        })
    # Two independent windows normally needed for uncertain anomalies,
    # BUT one reliably voiced window with >4 semitone systematic F0 error
    # is enough to reject the track. Former logic leaked such bad 35s mixes.
    confirmed_pitch_shift = any(
        r["issue"] == "large_unrequested_pitch_shift"
        and r["expected_voiced_frames"] >= 300
        and r["actual_voiced_frames"] >= 240
        for r in reports
    )
    status = ("rejected" if confirmed_pitch_shift or severe >= 2
              else "review" if severe else "not_flagged")
    return {
        "status": status,
        "severe_windows": severe,
        "window_count": len(reports),
        "windows": reports,
        "reason": {
            "rejected": "Перенос голоса нарушил высоту мелодии или потерял вокал в нескольких участках. Оставлен исходный трек.",
            "review": "На одном участке возможен сдвиг регистра или потеря вокала. Проверь результат на слух.",
            "not_flagged": "Крупного систематического сдвига мелодии не найдено. Естественность не подтверждена.",
        }[status],
        "identity_verified": False,
        "pronunciation_verified": False,
        "natural_singing_verified": False,
    }


def inspect_song(conditioned_f0, converted_wave_16k, f0_extractor, sample_rate=16000):
    signal = np.asarray(converted_wave_16k, dtype=np.float32).ravel()
    source = np.asarray(conditioned_f0, dtype=np.float32).ravel()
    duration = len(signal) / sample_rate
    if duration < 8 or len(source) < 50:
        return {"status": "not_proven", "reason": "Недостаточно материала для проверки мелодии.",
                "windows": [], "identity_verified": False}
    span = min(24.0, duration)
    if duration <= 35:
        starts = [0.0]
    elif duration <= 75:
        starts = [0.0, duration - span]
    else:
        starts = [0.0, (duration - span) / 2, duration - span]
    pairs = []
    for start in starts:
        a = round(start * sample_rate)
        b = min(len(signal), round((start + span) * sample_rate))
        # Map source RMVPE frame positions to the same time region.
        fa = min(len(source), round(start / duration * len(source)))
        fb = min(len(source), round((start + span) / duration * len(source)))
        observed = np.asarray(f0_extractor(signal[a:b], thred=0.03), dtype=float).ravel()
        pairs.append({"start_s": start, "expected": source[fa:fb], "actual": observed})
    return evaluate_pairs(pairs)

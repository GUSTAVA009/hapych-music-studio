"""Voice integrity checks for long Russian-language songs.
Keep source/converted identity distinct. Screen catastrophic loss; do not
misclassify 50 short acoustic energy dips across 140 seconds as a failed song.
No audio replacement, no identity claims, no pitch changes.
"""
import json
from pathlib import Path
from voice_guard24 import energy,transcriptions,words,edit_distance

def assess_energy(measure):
    seconds=float(measure.get("analysis_seconds") or 0)
    duration_error=abs(float(measure.get("duration_error") or 0))
    active_frames=int(measure.get("active_frames") or 0)
    missing_frames=int(measure.get("drop_frames") or 0)
    ratio=missing_frames/max(1,active_frames)
    segments=measure.get("drop_segments") or []
    longest=max((float(x["end"])-float(x["start"]) for x in segments),default=0.0)
    deep=[x for x in segments if (float(x["end"])-float(x["start"])>=.22
                                and float(x.get("minimum_relative_db",0))<=-30)]
    metrics={
      "duration_seconds":round(seconds,2),
      "relative_missing_vocal_frames":round(ratio,5),
      "longest_energy_dip_s":round(longest,3),
      "deep_dropout_events":len(deep),
      "energy_dip_events":len(segments),
      "duration_error_s":round(duration_error,4),
    }
    info={
      "status":"passed_checks","accepted":True,"perceptual_quality_verified":False,
      "speaker_similarity_verified":False,
      "asr_checked":False,"metrics":metrics,
      "reason":"Длительность вокала сохранена. Автоматическая проверка не обнаружила критических выпадений.",
    }
    if duration_error>.18:
      info.update(status="rejected",accepted=False,
          reason="Длина вокальной дорожки изменилась; перенос сохранён только в диагностике.")
    elif not measure.get("reliable") or active_frames<80:
      info.update(status="not_proven",accepted=False,
          reason="Слишком мало надёжного вокального сигнала для проверки.")
    elif ratio>.27 or longest>=.70 or len(deep)>=2 or (ratio>.075 and len(segments)>=12) or (longest>=.18 and len(segments)>=15):
      info.update(status="rejected",accepted=False,
          reason="Обнаружены множественные заметные провалы вокала; повреждённый перенос не публикуется, исходная дорожка сохранена.")
    elif ratio>.045 or longest>=.15 or len(segments)>=4:
      info.update(status="warning",accepted=True,
          reason="Перенос создан, но есть короткие перепады уровня вокала. Прослушай итог: естественность не подтверждена.")
    return info

def check(source,converted,report_path,language='unknown'):
    measure=energy(source,converted)
    result=assess_energy(measure)
    # Whisper can mistake music, backing vocals and silence for missing words.
    # For borderline cases where measurements are uncertain, ASR may provide
    # additional evidence; never reject solely on a 24-second ASR discrepancy.
    metric=result["metrics"]
    borderline=(result["status"]=="warning" and metric["relative_missing_vocal_frames"]>.18)
    if borderline:
      try:
        before,after=transcriptions(source,converted,language)
        a,b=words(before),words(after)
        ratio=edit_distance(a,b)/max(len(a),1)
        result["asr_checked"]=True
        result["asr_source_words"]=len(a)
        result["asr_converted_words"]=len(b)
        result["asr_edit_ratio"]=round(ratio,4)
        if len(a)>=10 and len(b)<len(a)*.25 and ratio>.75:
          result.update(status="not_proven",accepted=False,
            reason="Вероятная значительная потеря разборчивости. Оставлен исходник.")
      except Exception as exc:
        result["asr_error"]=str(exc)[:160]
    result["energy"]=measure
    result["checker"]="voice_guard42"
    result["meaning"]="Checks catastrophic audio damage only; does not certify voice identity, Russian pronunciation, or naturalness."
    Path(report_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

"""Conservative user-voice integrity gate.
No audio modification. Avoid labelling an unsafe timbre transfer "my voice".
"""
from pathlib import Path
import json
from voice_guard24 import energy, transcriptions, words, edit_distance

def assess(measure, before=None, after=None, asr_available=True):
    result={'status':'passed_checks','accepted':True,'perceptual_quality_verified':False,
            'reason':'Автоматические проверки не обнаружили грубой порчи, но естественность не подтверждена.'}
    if abs(float(measure.get('duration_error',0)))>.12:
        result.update(status='rejected',accepted=False,
                      reason='После переноса изменилась длительность вокальной дорожки.')
        return result
    if not measure.get('reliable'):
        result.update(status='rejected',accepted=False,
                      reason='Недостаточно надёжного вокала для проверки переноса тембра.')
        return result
    segments=measure.get('drop_segments',[])
    deep=[s for s in segments if float(s.get('minimum_relative_db',0))<=-15]
    extended=[s for s in deep if float(s['end'])-float(s['start'])>=.10]
    if len(deep)>=2 or extended:
        result.update(status='rejected',accepted=False,
                      reason='Обнаружены резкие провалы голоса после переноса тембра; исходный певец сохранён.')
        return result
    if asr_available and before is not None and after is not None:
        source_words=words(before);output_words=words(after)
        distance=edit_distance(source_words,output_words)
        ratio=distance/max(len(source_words),1)
        result.update(asr_source=before,asr_converted=after,
                      asr_edit_distance=distance,asr_difference=round(ratio,4),
                      asr_checked_seconds=24)
        if len(source_words)>=10 and distance>=5 and ratio>.30:
            result.update(status='rejected',accepted=False,
                          reason='После переноса заметно изменилось распознавание слов; исходный певец сохранён.')
        elif len(source_words)>=6 and len(output_words)<len(source_words)*.45:
            result.update(status='rejected',accepted=False,
                          reason='После переноса исчезла значительная часть распознаваемых слов.')
        elif segments:
            result.update(status='rejected',accepted=False,
                          reason='Выявлены короткие провалы вокала. Бракованный перенос не публикуется.')
        elif len(source_words)<5:
            result.update(status='not_proven',accepted=False,
                          reason='Недостаточно разборчивых слов для проверки личного голоса.')
    elif segments or not asr_available:
        result.update(status='not_proven',accepted=False,
                      reason='Нельзя подтвердить отсутствие повреждения вокала; использован исходный певец.')
    return result

def check(source,converted,report_path,language='unknown'):
    measure=energy(source,converted)
    preliminary=assess(measure,asr_available=True)
    if preliminary['status']=='rejected':
        report=preliminary
    else:
        try:
            before,after=transcriptions(source,converted,language)
            report=assess(measure,before,after,asr_available=True)
        except Exception as exc:
            report=assess(measure,asr_available=False)
            report['diagnostic_error']=str(exc)[:180]
    report['energy']=measure
    report['checker']='voice_guard25'
    report['meaning']='Integrity checks only. No guarantee of speaker similarity or studio-quality singing.'
    Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

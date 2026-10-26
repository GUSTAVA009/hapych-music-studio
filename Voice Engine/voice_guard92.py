"""QA92 conservative Russian lyric regression screen after Seed-VC conversion.

Improves *fail-closed* artifact routing, not the model. Reuses local Whisper
for warning cases only. Never postulates that voice identity or timbre is proved.
No raw user audio leaves device.
"""
from pathlib import Path
import json
import voice_guard42
from voice_guard24 import words,edit_distance,transcriptions

def _word_ending_tokens(tokens):
    return [w for w in tokens if w.endswith(("ешь","ишь","ешься","ишься","шь")) and len(w)>=5]

def check(source,converted,report_path,language="unknown"):
    res=voice_guard42.check(source,converted,report_path,language)
    res["checker"]="voice_guard92"
    res["pronunciation_human_verified"]=False
    res["timbre_identity_human_verified"]=False
    res["linguistic_gate"]="not_run"
    # Reject decisions already made by voice_guard42 are final. Whisper can
    # be noisy on sung harmonies; only compare the FIRST 24s on warning tracks.
    if (str(language).lower().startswith("ru") and
            res.get("status")=="warning" and res.get("accepted")):
        try:
            before,after=transcriptions(source,converted,"ru")
            a,b=words(before),words(after)
            delta=edit_distance(a,b)
            rate=delta/max(len(a),1)
            lost_suffix=max(0,len(_word_ending_tokens(a))-len(_word_ending_tokens(b)))
            q={
               "reference_words":len(a),"converted_words":len(b),
               "word_edit_distance":delta,
               "relative_word_edit_rate":round(rate,4),
               "source_russian_ending_words":len(_word_ending_tokens(a)),
               "converted_russian_ending_words":len(_word_ending_tokens(b)),
               "possible_missing_word_endings":lost_suffix,
               "window_seconds":24,
               "asr_not_phoneme_ground_truth":True}
            res.update(asr_checked=True,linguistic_gate="screened",
                       linguistic_comparison=q)
            severe=(len(a)>=12 and delta>=8 and rate>=.65 and len(b)<len(a)*.8)
            if severe:
                res.update(status="rejected",accepted=False,
                    reason=("После переноса голоса значительно ухудшилась "
                      "разборчивость слов по независимой ASR-проверке. "
                      "Вместо неестественной версии оставлен исходный трек; "
                      "твой тембр не заявляется применённым."),
                    linguistic_gate="rejected_severe_lexical_loss")
            elif len(a)<8:
                res.update(linguistic_gate="insufficient_lyric_content")
            elif rate>.30 or lost_suffix>=2:
                res.update(status="warning",
                    reason=str(res.get("reason",""))+
                        " Автопроверка обнаружила возможные изменения русских слов "
                        "и окончаний; обязательно прослушай результат.")
        except Exception as exc:
            res.update(asr_checked=False,linguistic_gate="not_verified",
                asr_error=str(exc)[:200],
                reason=str(res.get("reason",""))+
                       " Точная проверка русских слов не завершилась.")
    Path(report_path).write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8")
    return res

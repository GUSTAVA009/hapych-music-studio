"""QA87: separate explicit vocal exclusions from positive music caption.

Purpose: send already-requested disallowed qualities to LM Negative Prompt,
instead of relying on model to interpret "No X" buried in positive caption.
No additional source audio, training, rewriting or alteration of owner lyrics.
This remains a model *instruction*, never a phoneme fidelity guarantee.
"""
from __future__ import annotations
import re

EN_HEAD=re.compile(r"\b(?:no|without|avoid|exclude)\s+([^.!?;\n]{2,150})",re.I)
RU_HEAD=re.compile(r"(?<![а-яё])(?:без|никаких|избегай|исключить)\s+([^.!?;\n]{2,150})",re.I)
ALIASES={
    "female": "female lead singing",
    "female vocals": "female lead singing",
    "female vocalist": "female lead singing",
    "женского вокала":"female lead singing",
    "женского голоса":"female lead singing",
    "женских голосов":"female lead singing",
    "male vocals": "male lead singing",
    "male": "male lead singing",
    "rap": "rap vocal delivery",
    "rapping": "rap vocal delivery",
    "рэпа": "rap vocal delivery",
    "речитатива": "rap vocal delivery",
    "autotune": "obvious autotune artifacts",
    "auto-tune": "obvious autotune artifacts",
    "автотюна": "obvious autotune artifacts",
    "robotic vibrato": "robotic pitch wobble",
    "harsh vibrato": "harsh vibrato",
    "robotic stutters": "robotic vocal stuttering",
    "stutters": "vocal stuttering",
    "foreign accent":"foreign-accented Russian",
    "шумов": "extraneous noise",
}
def _flatten_negative(value):
    pieces=[]
    for phrase in EN_HEAD.findall(value)+RU_HEAD.findall(value):
        for chunk in re.split(r",\s*|\s+or\s+|\s+and\s+|\s+или\s+|\s+и\s+",phrase,flags=re.I):
            key=re.sub(r"^(?:no|without|avoid|без)\s+","",chunk.strip(),flags=re.I).lower()
            key=re.sub(r"\s+"," ",key).strip(" .,")
            if not key:continue
            key=ALIASES.get(key,key)
            if key not in pieces:pieces.append(key)
    return pieces
def add_constraints(style:str,language:str,original_negative:str):
    explicit=_flatten_negative(str(style or ""))
    base=[chunk.strip() for chunk in str(original_negative or "").split(",") if chunk.strip()]
    extra=[]
    if str(language).lower()=="ru":
        extra += ["missing Russian word endings","swallowed Russian consonants","chopped vowels"]
    if re.search(r"(?<!\w)(?:baritone|баритон)(?!\w)",str(style or ""),re.I):
        extra += ["unintentional falsetto","unnaturally high pitched lead"]
    clean=[]
    for part in base+explicit+extra:
        if part.lower() not in {p.lower() for p in clean}:
            clean.append(part)
    result=", ".join(clean)
    # Omit generic extras first, explicit user prohibitions never silently skipped.
    if len(result)>500:
        clean=[x for x in base+explicit if x.lower() not in set()]
        clean=list(dict.fromkeys(clean))
        result=", ".join(clean)[:500].rsplit(",",1)[0]
    return {"negative_prompt":result,"explicit_negative_terms":explicit,
       "dynamic_guard_terms":extra,
       "does_not_guarantee_musical_compliance":True}

def syllable_health(lyrics:str,duration_seconds:int):
    # Detect density; no rewriting, and ignore section labels.
    lines=[x.strip() for x in str(lyrics or "").splitlines()
        if x.strip() and not x.lstrip().startswith("[")]
    syllables=[len(re.findall("[аеёиоуыэюя]",line.lower())) for line in lines]
    total=sum(syllables)
    if not duration_seconds:return {"warning":None,"syllables":total,"lines":len(lines)}
    density=total/max(1,duration_seconds*0.75)
    risk=max(syllables,default=0)>24 or density>4.8
    message=("Много слогов для выбранной длительности: окончания слов могут съедаться; "
        "текст сохранён без изменений. Рассмотри более долгий трек или сокращение текста.") if risk else None
    return {"warning":message,"syllables":total,"lines":len(lines),
            "effective_syllables_per_second":round(density,2),
            "max_line_syllables":max(syllables,default=0),
            "requires_review":risk}

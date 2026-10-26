"""Condition ACE-Step for arranged beginnings and endings, without truncation.
The 512-char caption and 4096-char lyric limits remain enforced. No musical
cadence is guaranteed by prompt guidance alone; post-master fade is separate.
"""
import re

def condition(lyrics,style,requested_seconds=-1,instrumental=False):
    original=str(lyrics or "")
    sec=float(requested_seconds or 0)
    if sec<=0:sec=180
    structure={"source_characters":len(original),"duration_assumed_seconds":sec,
               "prelude_added":False,"coda_added":False,
               "notes":[],"all_user_words_retained":True,
               "arrangement_guaranteed":False}
    if instrumental or original.strip()=="[Instrumental]":
        return original,structure
    s=str(style or "")
    skip_intro=bool(re.search(r"immediate\s+(?:vocal|hook)|сразу\s+(?:вокал|припев)|no\s+intro",s,re.I))
    already_intro=bool(re.search(r"^\s*\[\s*(?:instrumental\s+intro|intro\s*-\s*instrumental)",original,re.I))
    already_outro=bool(re.search(r"\[\s*(?:instrumental\s+outro|outro\s*-\s*instrumental)",original,re.I))
    bars=1 if sec<35 else 2 if sec<85 else 4
    prelude=("[Intro - "+str(bars)+" bars, gradual instrumental opening, no lead vocals]\n")
    coda=("\n[Outro - "+str(bars)+" bars, instrumental resolution, final chord, drums settle, long reverb tail]")
    prefix="" if (skip_intro or already_intro) else prelude
    suffix="" if already_outro else coda
    proposed=prefix+original.strip()+suffix
    if len(proposed)<=4096:
        structure["prelude_added"]=bool(prefix)
        structure["coda_added"]=bool(suffix)
        structure["guided_characters"]=len(proposed)
        words=len(re.findall(r"[а-яёa-z0-9'-]+",re.sub(r"\[[^\]]+\]"," ",original),re.I))
        available=max(1,sec-bars*4*60/max(30,float(re.search(r"\b(\d{2,3})\s*BPM",s,re.I).group(1)) if re.search(r"\b(\d{2,3})\s*BPM",s,re.I) else 100)*2)
        structure["words_per_available_second"]=round(words/available,3)
        if words/available>3.0:
            structure["notes"].append("Dense vocals for this duration; increase length or shorten lyrics to avoid cut words.")
        structure["notes"].append("Intro and outro are prompt guidance; final master always shapes endpoints separately.")
        return proposed,structure
    structure["guided_characters"]=len(original)
    structure["notes"].append("Could not add separate intro/outro tags: 4096-char ACE-Step lyric limit. Original lyrics unchanged.")
    return original,structure

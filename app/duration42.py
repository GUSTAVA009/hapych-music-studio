"""Interpret only explicit song-duration instructions; 0 is still genuine auto.
Keep manual UI duration highest-priority; no music quality parameters modified.
"""
from __future__ import annotations
import re
def resolve_duration(manual_duration, description):
    manual=int(manual_duration or 0)
    if manual:
        if not 10<=manual<=480:raise ValueError("Продолжительность — от 10 до 480 секунд")
        return manual,"manual"
    text=str(description or "")
    minpat=r"(?<![\w\d])(\d{1,2}(?:[.,]\d+)?)\s*(?:min(?:ute)?s?|мин(?:ут[ыа]?)?)(?!\w)"
    secpat=r"(?<![\w\d])(\d{1,3})\s*(?:s(?:ec(?:ond)?s?)?|сек(?:унд[ыа]?|унды)?)(?!\w)"
    # Do not interpret a 3/4 time signature, BPM number or genre as duration.
    minutes=list(re.finditer(minpat,text,re.I))
    seconds=list(re.finditer(secpat,text,re.I))
    durations=[]
    for m in minutes:
        secs=round(float(m.group(1).replace(",","."))*60)
        adjoining=next((x for x in seconds if 0<=x.start()-m.end()<=7),None)
        if adjoining:secs+=int(adjoining.group(1))
        if 10<=secs<=480:durations.append((m.start(),secs))
    for s in seconds:
        if any(0<=s.start()-m.end()<=7 for m in minutes):continue
        secs=int(s.group(1))
        if 10<=secs<=480:durations.append((s.start(),secs))
    if durations:
        durations.sort()
        return durations[0][1],"prompt"
    return -1,"automatic"

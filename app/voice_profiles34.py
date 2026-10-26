"""Universal local singer profiles for Music Studio 34.

Profiles are metadata and speaker boundaries, NOT claimed speaker embeddings or
trained checkpoints. A selected reference must belong to the specified artist.
No cross-speaker concatenation, checkpoint reuse or automatic identity matching.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,re,threading,uuid,os

ROOT=Path.home()/"Music Studio"
DB=ROOT/"Voice Profiles"/"profiles.json"
VOICES=ROOT/"Мой голос"
LOCK=threading.RLock()
SUPPORTED={".wav",".mp3",".flac",".ogg",".m4a",".aac"}
def _load():
    if not DB.exists():return {"version":1,"profiles":[],"assignments":{}}
    value=json.loads(DB.read_text(encoding="utf-8"))
    if not isinstance(value.get("profiles"),list) or not isinstance(value.get("assignments"),dict):
        raise ValueError("Damaged voice profiles database")
    return value
def _save(state):
    DB.parent.mkdir(parents=True,exist_ok=True)
    tmp=DB.with_name("profiles."+uuid.uuid4().hex+".tmp")
    try:
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,DB)
    finally:tmp.unlink(missing_ok=True)
def _clean_name(value):
    s=" ".join(str(value or "").split())
    if len(s)<2 or len(s)>65 or any(ord(c)<32 for c in s):
        raise ValueError("Name must be 2-65 printable characters")
    return s
def _valid_file(name,folder=VOICES):
    # Do not accept paths or move recordings out of the central flat archive.
    raw=str(name or "")
    if not raw or "\\" in raw or "/" in raw or raw in (".",".."):
        raise ValueError("Invalid recording name")
    p=(folder/raw).resolve()
    if p.parent!=folder.resolve() or p.suffix.lower() not in SUPPORTED or not p.is_file():
        raise ValueError("Recording does not exist in local voice library")
    return p
def list_profiles():
    with LOCK:
        data=_load()
        return {"profiles":data["profiles"],
                "recording_count":len(data["assignments"]),
                "unassigned_recordings":sum(p.is_file() and p.suffix.lower() in SUPPORTED and p.name not in data["assignments"] for p in VOICES.iterdir()) if VOICES.exists() else 0,
                "trained_checkpoints_are_isolated":False,
                "storage":"local"}
def create_profile(name,permission,language="ru"):
    if permission is not True:raise ValueError("Explicit voice-owner permission required")
    name=_clean_name(name)
    lang=str(language or "ru").lower()
    if lang not in ("ru","en","auto"):lang="auto"
    with LOCK:
        data=_load();pid="artist_"+uuid.uuid4().hex[:20]
        entry={"id":pid,"name":name,"language":lang,
               "created":datetime.now(timezone.utc).isoformat(),
               "rights_confirmed":True,"checkpoint":None,
               "trained_model_verified":False}
        data["profiles"].append(entry)
        _save(data)
        return dict(entry)
def assign(name,profile_id,permission,allow_reassign=False,folder=VOICES):
    if permission is not True:raise ValueError("Explicit voice owner permission required")
    file=_valid_file(name,folder)
    pid=str(profile_id or "")
    with LOCK:
        state=_load()
        if pid not in {x["id"] for x in state["profiles"]}:
            raise ValueError("Unknown artist profile")
        earlier=state["assignments"].get(file.name)
        if earlier and earlier["profile_id"]!=pid and not allow_reassign:
            raise ValueError("Recording already belongs to another artist; explicit reassignment required")
        state["assignments"][file.name]={"profile_id":pid,
                                        "rights_confirmed":True,
                                        "assigned":datetime.now(timezone.utc).isoformat()}
        _save(state)
        return {"name":file.name,"profile_id":pid,"ok":True}
def assignment(name):
    with LOCK:
        return dict(_load()["assignments"].get(str(name),{}))
def validate_reference(name,profile_id):
    # A missing profile is permitted only for a legacy unassigned recording.
    record=assignment(name)
    current=str(record.get("profile_id") or "")
    requested=str(profile_id or "")
    if current!=requested:
        raise ValueError("Voice belongs to a different singer profile. Select the matching profile.")
    return {"profile_id":current or None,"matched":True,
            "model_policy":"base_zero_shot; no cross-artist fine-tuned model",
            "single_recording_reference":True}
def remove_assignment(name):
    with LOCK:
        data=_load()
        if name in data["assignments"]:
            data["assignments"].pop(name)
            _save(data)

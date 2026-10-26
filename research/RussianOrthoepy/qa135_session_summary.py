from pathlib import Path
import json,sys
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
files=sorted((R/"Исходные версии").glob("*.session.json"),key=lambda p:p.stat().st_mtime,reverse=True)
f=files[0];print("SESSION",f.name)
j=json.loads(f.read_text(encoding="utf8"))
print("SESSION_KEYS",list(j))
req=j.get("requested",{})
print("REQUEST_FIELDS",[(k,repr(v)[:320]) for k,v in req.items() if k not in ("lyrics","style")])
print("TITLE",req.get("title",""))
print("LYRICS_HEAD",repr(req.get("lyrics","")[:260]))
print("STYLE",req.get("style","")[:600])
print("ENGINE_LYRICS_LENGTH",len(j.get("engine_settings",{}).get("Lyrics","")))
for x in j.get("files",[]):print("TRACK",x.get("name"),"VOICE",x.get("voice_applied"),"TITLE",x.get("title"),"PROFILE",x.get("voice_profile_id"))

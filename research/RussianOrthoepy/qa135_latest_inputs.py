from pathlib import Path
import json,re,sys
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
p=R/"app"/"requests"/"286c27593c324d189fa9141425398351.json"
j=json.loads(p.read_text(encoding="utf8"))
print("TOP_KEYS",list(j))
for k,v in j.items():
 print("FIELD",k,"TYPE",type(v).__name__)
 if isinstance(v,dict):
  print("SUBKEYS",k,list(v.keys())[:95])
  if k in ("settings","data","request"):
   for kk,vv in v.items():
    if isinstance(vv,(dict,list)):print("SETTING",kk,repr(vv)[:140])
    else:print("SETTING",kk,repr(vv)[:300])
print("PREP_CAPTION",repr(j.get("preparation",{}).get("caption",""))[:550])
print("PREP_LYRIC_LINES",len(j.get("preparation",{}).get("lyrics","").splitlines()))
for k in ("voice_profile_id","voice","use_voice","variants","duration","title","style","lyrics"):
 if k in j:print("ROOT",k,repr(j[k])[:200])

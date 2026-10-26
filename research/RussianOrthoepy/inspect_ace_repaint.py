"""Inspect live ACE-Step repaint API inputs without changing studio."""
import requests,json
s=requests.Session();s.trust_env=False
r=s.get("http://127.0.0.1:7862/config",timeout=9);r.raise_for_status()
c=r.json()
api=next(x for x in c["dependencies"] if x.get("api_name")=="generation_wrapper")
comps={x["id"]:x for x in c["components"]}
for n,id in enumerate(api["inputs"]):
 co=comps[id];p=co.get("props",{});name=p.get("label") or p.get("name") or ""
 if any(z in name.lower() for z in ("task","source","repaint","start","end","reference","audio duration","caption","lyrics","seed","think","infer","cover")):
  raw=p.get("value");raw="<complex>" if isinstance(raw,(list,dict)) else raw
  print("ACE_INPUT",n,id,co["type"],repr(name),repr(raw)[:140],flush=True)

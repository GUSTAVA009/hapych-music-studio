import requests
s=requests.Session();s.trust_env=False
c=s.get("http://127.0.0.1:7862/config",timeout=8).json()
d=next(x for x in c["dependencies"] if x.get("api_name")=="generation_wrapper")
a={x["id"]:x for x in c["components"]}
for n,i in enumerate(d["inputs"]):
 x=a[i];p=x.get("props",{});lab=p.get("label") or p.get("name") or ""
 print(n,x["type"],i,repr(lab),repr(p.get("value"))[:120],flush=True)

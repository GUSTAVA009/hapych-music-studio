import json,re,sys,time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from ruaccent import RUAccent
root=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"
data=json.loads((root/"QA123_context_cases.json").read_text(encoding="utf-8"))
accent=RUAccent()
accent.load(omograph_model_size="tiny",use_dictionary=True,device="CPU",tiny_mode=False,workdir=str(root/"models"))
lines=data["lyrics"].splitlines()
results=[]
for i,line in enumerate(lines,1):
    prediction=accent.process_all(line)
    print(str(i)+": "+prediction,flush=True)
    results.append({"line":i,"raw":line,"ruaccent":prediction,"expected":[x for x in data["expected"] if x["line"]==i]})
out=root/"QA123_context_results.json"
out.write_text(json.dumps({"model":"RUAccent 1.5.8.3 tiny CPU","scope":"text-side testing; no ACE-Step or studio modifications","results":results},ensure_ascii=False,indent=2),encoding="utf-8")
print("RESULTS_SAVED "+str(out),flush=True)

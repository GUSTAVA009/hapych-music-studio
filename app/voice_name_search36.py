from pathlib import Path
import json
r=Path.home()/"Music Studio"
targets=[r/"Мой голос",r/"Voice Profiles",r/"Voice Engine"/"training_dataset",r/"Training Runs"]
needle=("илья","ильи","ilya","ilia","il'ya")
for path in targets:
 if not path.exists():continue
 names=[]
 hits=[]
 for f in path.rglob("*"):
  if not f.is_file():continue
  if any(s in f.name.casefold() for s in needle):names.append(str(f.relative_to(r)))
  if f.suffix.lower() in (".json",".txt",".yml",".yaml",".csv",".md") and f.stat().st_size<200000:
   try:
    data=f.read_text(encoding="utf-8",errors="replace")
    if any(s in data.casefold() for s in needle):hits.append(str(f.relative_to(r)))
   except Exception:pass
 print("SEARCH",str(path),"FILENAME",json.dumps(names[:30],ensure_ascii=True),"TEXT",json.dumps(hits[:30],ensure_ascii=True),flush=True)

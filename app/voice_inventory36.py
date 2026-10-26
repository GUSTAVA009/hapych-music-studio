from pathlib import Path
import json,subprocess
R=Path.home()/"Music Studio"
folder=R/"Мой голос"
for f in sorted(folder.iterdir()):
 if not f.is_file():continue
 row={"name":f.name,"bytes":f.stat().st_size,"extension":f.suffix}
 if f.suffix.lower() in {".wav",".mp3",".m4a",".flac",".ogg"}:
  p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=sample_rate,channels","-of","json",str(f)],capture_output=True,text=True)
  try:row["audio"]=json.loads(p.stdout)
  except:row["ffprobe_error"]=p.stderr[-200:]
 if f.suffix.lower()==".json":
  try:row["content"]=json.loads(f.read_text(encoding="utf-8"))
  except:pass
 print(json.dumps(row,ensure_ascii=True),flush=True)
for path in [R/"Voice Profiles"/"profiles.json",R/"Training Runs"/"voice32"/"dataset_manifest.json",R/"Training Runs"/"voice32"/"result.json"]:
 if path.exists():
  print("META",str(path),json.dumps(json.loads(path.read_text(encoding="utf-8")),ensure_ascii=True)[:10000],flush=True)
for root in [R/"Voice Engine",R/"Training Runs"]:
 print("TRAIN_FILES",str(root))
 files=[]
 for f in root.rglob("*"):
  if f.is_file() and f.suffix.lower() in (".json",".yaml",".yml",".txt") and ("dataset" in f.name.lower() or "manifest" in f.name.lower() or "profile" in f.name.lower()) and f.stat().st_size<90000:
   files.append(str(f))
 print(json.dumps(files[:35],ensure_ascii=True))

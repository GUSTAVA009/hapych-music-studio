"""Validate external ApexSVC checkpoints without arbitrary pickle code execution.
No model inference, no user data accesses. Only safe torch tensor loads.
"""
from pathlib import Path
import json,torch,sys,time,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA75";D.mkdir(parents=True,exist_ok=True)
c=R/"Voice Engine"/"alternatives"/"ApexSVC"/"checkpoints"
paths=[c/"WavLM-Large.pt",c/"G_150k.pt"]
assert all(p.is_file() and p.stat().st_size>20000000 for p in paths)
report={}
for p in paths:
 t=time.monotonic()
 ckpt=torch.load(str(p),map_location="cpu",weights_only=True)
 assert isinstance(ckpt,dict)
 name=p.name
 if "WavLM" in name:
  assert "cfg" in ckpt and "model" in ckpt
  assert isinstance(ckpt["model"],dict) and len(ckpt["model"])>100
  desc={"cfg_type":str(type(ckpt["cfg"])),"config_string":str(ckpt["cfg"])[:500],
  "model_key_count":len(ckpt["model"])}
 else:
  assert "generator" in ckpt
  assert isinstance(ckpt["generator"],dict) and len(ckpt["generator"])>20
  desc={"generator_tensors":len(ckpt["generator"])}
 report[name]={"bytes":p.stat().st_size,"load_safe_seconds":round(time.monotonic()-t,2),"structure":desc}
 print("QA75_SAFE_CKPT",json.dumps({name:report[name]},ensure_ascii=True),flush=True)
 del ckpt
(D/"qa75_safe_checkpoint_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA75_ALL_WEIGHTS_SAFE_LOADED",flush=True)

"""Isolated ApexSVC official NeuCoSVC2 weight fetch, never touch production."""
from pathlib import Path
import os,sys,time,json
import gdown
R=Path.home()/"Music Studio"
ck=R/"Voice Engine"/"alternatives"/"ApexSVC"/"checkpoints"
ck.mkdir(parents=True,exist_ok=True)
target=ck/"G_150k.pt"
tmp=ck/"G_150k.pt.part"
if target.exists() and target.stat().st_size>20000000:
 print("APEX_VOCODER_ALREADY_PRESENT",target.stat().st_size,flush=True)
 sys.exit(0)
if tmp.exists():tmp.unlink()
url="https://drive.google.com/uc?id=1yDnT4Ah8Nlzq3QIff4ur4rz5CVpwYoip"
start=time.monotonic()
print("DOWNLOAD_APEX_G150K_FROM_UPSTREAM",flush=True)
res=gdown.download(url,str(tmp),quiet=False)
if not res or not tmp.exists():
 print("DOWNLOAD_FAILED",res,flush=True)
 sys.exit(3)
size=tmp.stat().st_size
if size<20000000:raise RuntimeError("Unexpectedly small model file, not installing")
os.replace(tmp,target)
print("APEX_G150K_READY",json.dumps({"bytes":size,"elapsed_s":round(time.monotonic()-start,2)},ensure_ascii=True),flush=True)

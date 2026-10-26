"""QA39 isolated high-detail ACE-Step SFT A/B against QA38 Turbo.
Same user lyrics, original seed, duration and tempo. Revised explicit voice/
chorus/outro directions. Output only to Diagnostics: no changes to song library.
"""
import os,sys,json,time,shutil,requests
from pathlib import Path
from gradio_client import Client
ROOT=Path.home()/"Music Studio";APP=ROOT/"app";sys.path.insert(0,str(APP))
from studio_server import prepare_request
from audio_guard55 import inspect_source
DIR=ROOT/"Diagnostics"/"QA39";DIR.mkdir(parents=True,exist_ok=True)
user=json.loads((ROOT/"Diagnostics"/"QA38"/"request.json").read_text(encoding="utf-8"))
old=json.loads((APP/"requests"/"d6dc780a0a0e460cb8e365b2a01ee647.json").read_text(encoding="utf-8"))
variants=json.loads((APP/"requests"/"d6dc780a0a0e460cb8e365b2a01ee647_variants.json").read_text(encoding="utf-8"))
prepared=prepare_request(user)
assert "4 low male backing harmonies" in prepared["caption"]
assert "resolved piano outro" in prepared["caption"]
assert "baritone" in prepared["caption"]
assert "4 low male backing harmonies" in prepared["lyrics"]
assert len(prepared["caption"])<=512
assert len(prepared["lyrics"])<=4096
settings=dict(old["settings"])
settings.update({"Music Caption":prepared["caption"],"Lyrics":prepared["lyrics"],
 "DiT Inference Steps":8,"Shift":3.0,"Batch Size":1,"Random Seed":False,
 "Seed":str(variants[0]["seed"]),"LM Temperature":0.78,"LM Batch Chunk Size":1})
assert settings["Audio Duration (seconds)"]==119 and settings["BPM (Beats Per Minute)"]==88
s=requests.Session();s.trust_env=False
config=s.get("http://127.0.0.1:7862/config",timeout=15).json()
dep=next(x for x in config["dependencies"] if x.get("api_name")=="generation_wrapper")
components={x["id"]:x for x in config["components"]}
args=[]
for cid in dep["inputs"]:
 c=components[cid]
 if c["type"]=="state":continue
 props=c.get("props",{})
 args.append(settings.get(props.get("label"),props.get("value")))
print("INPUT_COUNT",len(args),flush=True)
assert len(args)==72
record={"generator":"ACE-Step Turbo corrected prompt","sft_url":"http://127.0.0.1:7862",
 "prompt":prepared["caption"],"lyrics":prepared["lyrics"],"seed":settings["Seed"],
 "duration":119,"bpm":88,"steps":8,"baseline_model":"ACE-Step Turbo","baseline_steps":8}
(DIR/"sft_request.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
client=Client("http://127.0.0.1:7862",verbose=False)
client.predict(False,api_name="/set_use_lora")
begin=time.monotonic()
job=client.submit(*args,api_name="/generation_wrapper")
while not job.done():
 if time.monotonic()-begin>1200:
  try:job.cancel()
  except Exception:pass
  raise TimeoutError("SFT comparator exceeded 20 minutes")
 time.sleep(1)
reply=job.result()
out_ids=[cid for cid in dep["outputs"] if not components[cid].get("skip_api",components[cid]["type"]=="state")]
values={components[cid].get("props",{}).get("label"):value for cid,value in zip(out_ids,reply)}
audio=values.get("🎵 Generated Music (Sample 1)")
if isinstance(audio,dict):audio=audio.get("value",audio.get("path"))
if not isinstance(audio,str) or not Path(audio).is_file():
 choices=[]
 for v in reply:
  if isinstance(v,dict):v=v.get("value",v.get("path"))
  if isinstance(v,str) and v.lower().endswith((".wav",".flac",".mp3")) and Path(v).is_file():choices.append(v)
 if not choices:raise RuntimeError("SFT did not return usable audio. "+str(reply)[:500])
 audio=choices[0]
inspect_source(audio)
out=DIR/("QA39_TURBO_corrected_same_seed"+Path(audio).suffix.lower())
shutil.copy2(audio,out)
record.update(result_file=str(out),result_bytes=out.stat().st_size,
 elapsed_seconds=round(time.monotonic()-begin,1),
 sft_lrc=str(values.get("Lyrics Timestamps (Sample 1)",""))[:40000],
 finished=True)
(DIR/"turbo_fixed_result.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA39_TURBO_GENERATION_OK",out,"SECONDS",record["elapsed_seconds"],"BYTES",out.stat().st_size,flush=True)

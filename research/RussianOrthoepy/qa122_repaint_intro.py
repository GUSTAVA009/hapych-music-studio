"""QA122 0-8s isolated Repaint test of first robotic singing phrase.
No phoneme strings are put into ACE-Step lyrics (its tokenizer does NOT
support phoneme-level controls). Original QA119-A is kept unchanged.
"""
from pathlib import Path
import json,os,time,hashlib,shutil,requests,sys
from gradio_client import Client,handle_file
import soundfile as sf
R=Path.home()/"Music Studio"
D=R/"Diagnostics"/"QA122-NativeIntroRepaint"
D.mkdir(parents=True,exist_ok=True)
src=R/"Diagnostics"/"QA119-RussianDiction"/"QA119_NativeRussianSource_A.wav"
original_json=R/"Diagnostics"/"QA119-RussianDiction"/"qa119_generation.json"
ref=json.loads(original_json.read_text(encoding="utf8"))
assert src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==ref["candidates"]["A"]["sha256"]
assert abs(sf.info(src).duration-42)<.05
lyrics=ref["lyrics"]
caption=("Russian acoustic melodic pop, 102 BPM, G minor, "
 "natural native Russian male baritone in low chest register, "
 "smooth continuous legato from the first sung syllable, "
 "clear Russian soft consonants and full word endings, "
 "no robotic voice, no spoken opening, no foreign accent, "
 "gentle piano and electric guitar, refined warm recording.")
assert len(caption)<512 and "услышишь" in lyrics
os.environ.update(NO_PROXY="127.0.0.1,localhost,::1",
 no_proxy="127.0.0.1,localhost,::1",HTTP_PROXY="",HTTPS_PROXY="",ALL_PROXY="")
s=requests.Session();s.trust_env=False
status=s.get("http://127.0.0.1:7870/api/status",timeout=6).json()
assert status.get("status") in ("idle","done","error"),status
cfg=s.get("http://127.0.0.1:7862/config",timeout=8).json()
dep=next(x for x in cfg["dependencies"] if x.get("api_name")=="generation_wrapper")
comps={x["id"]:x for x in cfg["components"]}
settings=dict(json.loads((R/"app"/"requests"/"d6dc780a0a0e460cb8e365b2a01ee647.json").read_text(encoding="utf8"))["settings"])
settings.update({
 "Music Caption":caption,"Lyrics":lyrics,"BPM (Beats Per Minute)":102,
 "Key":"G minor","Time Signature":"4/4","Vocal Language":"ru",
 "Audio Duration (seconds)":42,
 "Batch Size":1,"DiT Inference Steps":8,
 "Random Seed":False,"Seed":"81225",
 "Reference Audio":None,"Source Audio":handle_file(str(src)),
 "Repainting Start":0.0,"Repainting End":8.0,
 "Repaint Mode":"balanced","Repaint Strength":0.52,
 "Instruction":"Fill the audio semantic mask based on the given conditions:",
 "Cover Strength (Melody Retention)":0.0,
 "Think":False,"CoT Metas (Chain-of-Thought Metadata)":False,
 "CoT Language Detection":False,"CaptionRewrite":False,"ParallelThinking":False,
 "LM Batch Chunk Size":1,"Audio Format":"wav",
 "Fade In (seconds)":0.0,"Fade Out (seconds)":0.0,"AutoGen":False
})
labels=[];params=[]
for i in dep["inputs"]:
 c=comps[i]
 if c["type"]=="state":continue
 label=c.get("props",{}).get("label")
 labels.append(label)
 params.append(settings.get(label,c.get("props",{}).get("value")))
assert params[labels.index("Repainting Start")]==0.0
assert params[labels.index("Repainting End")]==8.0
assert params[labels.index("Lyrics")]==lyrics
assert params[labels.index("Source Audio")] is not None
report={"status":"running","source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
  "repaint_window_s":[0.0,8.0],"vocal_language":"ru",
  "full_original_lyrics_kept":True,
  "preserves_original_QA119_wav":True,
  "model":"ACE-Step 1.5 local repaint","working_studio_not_modified":True,
  "not_a_1_to_1_voice_clone":True}
(D/"qa122_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
start=time.monotonic()
print("QA122_REPAINT_START",flush=True)
client=Client("http://127.0.0.1:7862",verbose=False)
job=client.submit(*params,api_name="/generation_wrapper")
while not job.done():
 if time.monotonic()-start>630:
  job.cancel()
  raise TimeoutError("Repaint longer than 10 mins")
 time.sleep(1)
result=job.result()
paths=[]
for v in result:
 if isinstance(v,dict):
  v=v.get("value",v.get("path"))
 if isinstance(v,str):
  p=Path(v)
  if p.is_file() and p.suffix.lower() in (".wav",".mp3",".flac"):
   paths.append(p)
assert paths,str(result)[-650:]
generated=paths[0]
target=D/("QA122_IntroRepaint_42s"+generated.suffix)
shutil.copy2(generated,target)
info=sf.info(target)
assert abs(info.duration-42)<1.5,info.duration
report.update(status="rendered",file=str(target),duration=round(info.duration,3),
  elapsed_seconds=round(time.monotonic()-start,2),
  sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
  human_intro_not_verified=True)
(D/"qa122_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
assert hashlib.sha256(src.read_bytes()).hexdigest()==report["source_sha256"]
print("QA122_REPAINT_GENERATED",json.dumps(report,ensure_ascii=True),flush=True)

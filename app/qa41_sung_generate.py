"""QA41 controlled sung QA39: remove contradictory 'spoken rap' cues.
Single same seed, BPM, key, lyrics, duration; never alters user library.
"""
import os,sys,json,time,shutil,re
from pathlib import Path
import requests
from gradio_client import Client
R=Path.home()/"Music Studio";APP=R/"app";sys.path.insert(0,str(APP))
from studio_server import prepare_request
from audio_guard55 import inspect_source
D=R/"Diagnostics"/"QA41";D.mkdir(exist_ok=True,parents=True)
orig=json.loads((R/"Diagnostics"/"QA38"/"request.json").read_text(encoding="utf-8"))
prior=json.loads((APP/"requests"/"d6dc780a0a0e460cb8e365b2a01ee647.json").read_text(encoding="utf-8"))
seeds=json.loads((APP/"requests"/"d6dc780a0a0e460cb8e365b2a01ee647_variants.json").read_text(encoding="utf-8"))
song=dict(orig)
song["title"]="QA41 - Тихий свет (мелодический вокал)"
song["style"]=("88 BPM, D minor. Cinematic urban Russian soulful ballad with dark piano, cello, strings, "
 "warm bass and organic drums. Natural expressive native Russian baritone. Connected melodic singing "
 "and sustained legato phrases in ALL verses and choruses, stable comfortable chest register, "
 "restrained human vibrato, soft register transitions, clean clear consonants. "
 "Four LOW male backing harmonies in choruses. Epic orchestral swell in middle; sax accents. "
 "Gradual soft intro; resolved piano outro and natural decay, wide organic stereo.")
oldlyrics=song["lyrics"]
replacements={
 "[Verse 1 - Natural Russian Male Baritone, Clear Spoken Rap, Unhurried]":
 "[Verse 1 - Warm Male Baritone, Sustained Melodic Singing, Smooth Legato Phrases]",
 "[Verse 2 - Intimate Russian Male Rap, Half-Time Piano]":
 "[Verse 2 - Warm Male Baritone Sung Melody, Continuous Pitched Phrases, Soft Piano]",
 "[Chorus - Deep Baritone, Four LOW Male Backing Voices, Wide Warm Harmonies]":
 "[Chorus - Sustained Sung Baritone Melody, Four LOW Male Backing Harmonies, Warm Stereo]",
 "[Final Chorus - Confident Deep Male Baritone, Four Low Male Harmony Voices, Big Drums]":
 "[Final Chorus - Sustained Sung Baritone, Four Low Male Harmony Voices, Powerful Drums]",
}
for before,after in replacements.items():
 if before not in song["lyrics"]:raise RuntimeError("Expected source verse tag absent: "+before)
 song["lyrics"]=song["lyrics"].replace(before,after)
assert not re.search(r"spoken|rap|речитатив|говорит",song["lyrics"]+" "+song["style"],re.I)
prepared=prepare_request(song)
caption=prepared["caption"]
print("CAPTION",caption,"LENGTH",len(caption),flush=True)
print("STRUCTURE",json.dumps(prepared["structure_plan"],ensure_ascii=True),flush=True)
print("SFX",[(x["effect"],x["supported"]) for x in prepared["effects_plan"]],flush=True)
assert len(caption)<=512 and len(prepared["lyrics"])<=4096
assert "connected melodic singing" in caption
assert "spoken" not in caption.lower()
assert not re.search(r"\brap\b",caption,re.I),caption
assert all(x["supported"] for x in prepared["effects_plan"])
data={"song":song,"compiled_caption":caption,"lyrics":prepared["lyrics"],"seed":str(seeds[0]["seed"]),
 "base_model":"ACE-Step v1.5 Turbo","DiT_steps":8,"duration":119,"bpm":88,
 "modified":"explicit sung verses and musical phrase constraints only","original_qa39_preserved":True}
(D/"QA41_sung_request.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
requests_client=requests.Session();requests_client.trust_env=False
h=requests_client.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("preparing","generating","converting")
assert not any(h.get(k,{}).get("active") for k in ("training32","training41","training23"))
cfg=requests_client.get("http://127.0.0.1:7862/config",timeout=14).json()
dep=next(x for x in cfg["dependencies"] if x.get("api_name")=="generation_wrapper")
components={c["id"]:c for c in cfg["components"]}
settings=dict(prior["settings"])
settings.update({"Music Caption":caption,"Lyrics":prepared["lyrics"],
                 "DiT Inference Steps":8,"Batch Size":1,"Random Seed":False,
                 "Seed":str(seeds[0]["seed"]),"LM Temperature":.78,"LM Batch Chunk Size":1})
arguments=[]
for cid in dep["inputs"]:
 c=components[cid]
 if c["type"]=="state":continue
 prop=c.get("props",{})
 arguments.append(settings.get(prop.get("label"),prop.get("value")))
assert len(arguments)==72
client=Client("http://127.0.0.1:7862",verbose=False)
client.predict(False,api_name="/set_use_lora")
start=time.monotonic()
job=client.submit(*arguments,api_name="/generation_wrapper")
while not job.done():
 if time.monotonic()-start>1800:
  try:job.cancel()
  except:pass
  raise TimeoutError("QA41 generation exceeded safe threshold")
 time.sleep(1)
result=job.result()
out_ids=[cid for cid in dep["outputs"] if not components[cid].get("skip_api",components[cid]["type"]=="state")]
mapped={components[cid].get("props",{}).get("label"):v for cid,v in zip(out_ids,result)}
audio=mapped.get("🎵 Generated Music (Sample 1)")
if isinstance(audio,dict):audio=audio.get("value",audio.get("path"))
if not isinstance(audio,str) or not Path(audio).is_file():
 for value in result:
  if isinstance(value,dict):value=value.get("value",value.get("path"))
  if isinstance(value,str) and value.lower().endswith((".wav",".mp3",".flac")) and Path(value).is_file():
   audio=value;break
if not isinstance(audio,str) or not Path(audio).is_file():
 raise RuntimeError("ACE-Step returned no audio. "+str(result)[-1200:])
inspect_source(audio)
out=D/("QA41_SungSource_same_seed"+Path(audio).suffix.lower())
shutil.copy2(audio,out)
data.update({"audio":str(out),"audio_bytes":out.stat().st_size,"elapsed_seconds":round(time.monotonic()-start,1)})
(D/"QA41_sung_result.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA41_SUNG_GENERATION_OK",json.dumps({k:data[k] for k in ("audio","audio_bytes","elapsed_seconds","DiT_steps")},ensure_ascii=True),flush=True)

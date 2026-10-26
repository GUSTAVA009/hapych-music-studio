"""QA45 new song in soft Russian neo-soul / acoustic pop.
Generates solely to Diagnostics; no original songs or models replaced.
"""
import os,sys,json,time,shutil,re
from pathlib import Path
import requests
from gradio_client import Client
R=Path.home()/"Music Studio";APP=R/"app";sys.path.insert(0,str(APP))
from studio_server import prepare_request
from audio_guard55 import inspect_source
D=R/"Diagnostics"/"QA45";D.mkdir(parents=True,exist_ok=True)
prior=json.loads((APP/"requests"/"d6dc780a0a0e460cb8e365b2a01ee647.json").read_text(encoding="utf-8"))
song={
"title":"QA45 - Там, где тепло",
"style":("Russian neo-soul acoustic pop, 76 BPM, A minor. Warm close-miked male baritone, "
"natural native Russian vowels and crisp consonants. Gentle connected melodic singing "
"throughout, soft legato, relaxed chest voice, restrained vibrato, no rap, no spoken phrases. "
"Intimate Rhodes piano, fingerpicked nylon guitar, round electric bass, soft brushed drums, "
"subtle strings and airy organic stereo. Gradual emotional rise, warm full chorus, "
"beautiful acoustic guitar bridge, calm piano outro, natural reverb and breath."),
"lyrics":"""[Intro - Soft Rhodes Piano, Fingerpicked Guitar, Gentle Fade In]
[Instrumental]

[Verse 1 - Gentle Male Baritone, Connected Melodic Singing, Soft Legato]
Город уснул за рекой.
Тёплый огонь над водой.
Я узнаю твои шаги,
Свет на ладонях береги.

Там, где кончается дождь,
Ты меня тихо найдёшь.
Ветер коснётся окна,
В комнате снова весна.

[Pre-Chorus - Warm Strings Rising, Sustained Notes]
И пусть дороги далеко,
С тобой мне дышится легко.
Слова не нужно торопить,
Достаточно тебя любить.

[Chorus - Warm Baritone, Smooth Sustained Singing, Gentle Male Harmonies]
Там, где тепло, где свет горит,
Сердце со мной заговорит.
Медленно, тихо, не спеша,
Снова поёт моя душа.

Там, где тепло, где рядом ты,
Станут реальными мечты.
Пусть этот вечер не уйдёт,
Музыка нас с тобой найдёт.

[Instrumental Break - Intimate Acoustic Guitar and Rhodes, Gradual Growth]

[Verse 2 - Mellow Baritone Singing, Clear Russian Diction]
Мы не считаем года,
Мимо бегут поезда.
В каждом мгновении опять
Есть что любить и что терять.

Если настанет рассвет,
Я сохраню этот свет.
Просто останься со мной,
Слушай, как дышит покой.

[Bridge - Emotional Strings, Spacious Melody, Quiet Breath]
И даже если день погас,
Я слышу музыку для нас.
В обычном свете фонарей
Мне стало чуточку теплей.

[Final Chorus - Full Warm Baritone, Wide Soft Harmonies, Gentle Crescendo]
Там, где тепло, где свет горит,
Сердце со мной заговорит.
Медленно, тихо, не спеша,
Снова поёт моя душа.

Там, где тепло, где рядом ты,
Станут реальными мечты.
Пусть этот вечер не уйдёт,
Музыка нас с тобой найдёт.

[Outro - Resolved Rhodes Piano, Guitar Harmonics, Slowly Fading]
Я сохраню этот свет.
Даже когда тебя нет.
[End]""",
"duration":167,"bpm":76,"two_versions":False,"use_voice":False,
"instrumental":False,"mode":"new","vocal_language":"ru"}
prepared=prepare_request(song)
assert len(prepared["caption"])<=512 and len(prepared["lyrics"])<=4096,(len(prepared["caption"]),len(prepared["lyrics"]))
assert "spoken" not in prepared["caption"].lower(),prepared["caption"]
assert "legato" in (prepared["caption"]+" "+prepared["lyrics"]).lower()
cfg={"song":song,"compiled_caption":prepared["caption"],"lyrics":prepared["lyrics"],
    "estimated_generation_seconds":167,"seed":924517,"steps":8,"model":"ACE-Step v1.5 Turbo",
    "human_accent_evaluation":False,"personal_voice_used":False}
(D/"qa45_request.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA45_CAPTION",prepared["caption"],flush=True)
print("QA45_LYRICS_LEN",len(prepared["lyrics"]),flush=True)
s=requests.Session();s.trust_env=False
health=s.get("http://127.0.0.1:7870/api/health",timeout=9).json()
assert health["job"]["status"] not in ("generating","preparing","converting")
assert not any(health.get(k,{}).get("active") for k in ("training23","training32","training41"))
c=s.get("http://127.0.0.1:7862/config",timeout=15).json()
dep=next(x for x in c["dependencies"] if x.get("api_name")=="generation_wrapper")
components={x["id"]:x for x in c["components"]}
settings=dict(prior["settings"])
settings.update({"Music Caption":prepared["caption"],"Lyrics":prepared["lyrics"],
 "Audio Duration (seconds)":167,"BPM (Beats Per Minute)":76,
 "DiT Inference Steps":8,"Batch Size":1,"Random Seed":False,
 "Seed":"924517","LM Temperature":.74,"LM Batch Chunk Size":1})
args=[]
for cid in dep["inputs"]:
 component=components[cid]
 if component["type"]=="state":continue
 props=component.get("props",{})
 args.append(settings.get(props.get("label"),props.get("value")))
assert len(args)==72
client=Client("http://127.0.0.1:7862",verbose=False)
client.predict(False,api_name="/set_use_lora")
job=client.submit(*args,api_name="/generation_wrapper")
start=time.monotonic()
while not job.done():
 if time.monotonic()-start>1800:
  try:job.cancel()
  except Exception:pass
  raise TimeoutError("Music generation exceeded 30 minutes")
 time.sleep(1)
reply=job.result()
out_ids=[cid for cid in dep["outputs"] if not components[cid].get("skip_api",components[cid]["type"]=="state")]
mapped={components[cid].get("props",{}).get("label"):v for cid,v in zip(out_ids,reply)}
music=mapped.get("🎵 Generated Music (Sample 1)")
if isinstance(music,dict):music=music.get("value",music.get("path"))
if not isinstance(music,str) or not Path(music).is_file():
 for v in reply:
  if isinstance(v,dict):v=v.get("value",v.get("path"))
  if isinstance(v,str) and Path(v).is_file() and v.lower().endswith((".wav",".flac",".mp3")):
   music=v;break
assert isinstance(music,str) and Path(music).is_file(),str(reply)[-800:]
inspect_source(music)
file=D/("QA45_NeoSoul_source"+Path(music).suffix.lower())
shutil.copy2(music,file)
cfg["audio"]=str(file);cfg["elapsed_seconds"]=round(time.monotonic()-start,1)
(D/"qa45_generation.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA45_GENERATED",file,file.stat().st_size,flush=True)

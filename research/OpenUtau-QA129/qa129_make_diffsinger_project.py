"""QA129 compile singer-specific USTX, keeping original note score and voicebank untouched.
For a multisyllabic word DiffSinger receives the whole word on its first note,
+ on continuation notes, consistent with the official OpenUtau phonemizer API.
"""
import json,yaml,copy,pathlib,hashlib,sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT=pathlib.Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
SCORE=ROOT/"QA129_Score"
SOURCE=SCORE/"QA129_RussianPhonemeScore.ustx"
doc=yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
sidecar=json.loads((SCORE/"QA129_phones.json").read_text(encoding="utf-8"))
syllables=sidecar["syllables"]
notes=doc["voice_parts"][0]["notes"]
assert len(notes)==len(syllables)==31
seen=set()
for note,syl in zip(notes,syllables):
 assert note["position"]==syl["tick"] and note["tone"]==syl["midi_note"]
 key=(syl["line"],syl["word_index"])
 if key not in seen:
  note["lyric"]=syl["word"]
  seen.add(key)
 else:
  note["lyric"]="+"
doc["name"]="HAPYCH QA129 - RU DiffSinger Keiro phoneme score"
doc["comment"]="Isolated noncommercial phonetic diction QA only; no production release or voice training. Keiro Revenant from LUNAI Project."
doc["tracks"][0]["singer"]="Keiro_Revenant_v170\\configs"
doc["tracks"][0]["phonemizer"]="OpenUtau.Core.DiffSinger.DiffSingerRussianPhonemizer"
doc["tracks"][0]["track_name"]="Keiro Revenant — RU diction control (not owner voice)"
doc["tracks"][0]["renderer_settings"]={"renderer":"DIFFSINGER"}
target=SCORE/"QA129_Keiro_RussianDiffSinger.ustx"
target.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=140),encoding="utf-8")
back=yaml.safe_load(target.read_text(encoding="utf-8"))
assert back["tracks"][0]["singer"]=="Keiro_Revenant_v170\\configs"
assert sum(n["lyric"]=="+" for n in back["voice_parts"][0]["notes"])==len(notes)-len(seen)
assert sum(n["duration"] for n in back["voice_parts"][0]["notes"])>0
print("QA129_KEIRO_USTX_VALID",len(notes),"NOTES",len(seen),"WORDS","PLUS_NOTES",sum(n["lyric"]=="+" for n in notes),flush=True)
print("QA129_KEIRO_PROJECT",target,flush=True)

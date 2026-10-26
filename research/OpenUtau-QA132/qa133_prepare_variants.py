"""QA133 isolated phonetic options.
A: speech-faithful дождь [doʂtʲ] and explicit мою [mɐju]
B: альтернативное мягкое дождь [doɕ:], same мою. Preserve original score.
No training/production edits. No changes to original lyric spelling.
"""
from pathlib import Path
import hashlib,json,copy,os,yaml
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
BASE=R/"QA132-KogdaPronunciation"
SRC=BASE/"QA132_Keiro_RussianCaseGuard.ustx"
D=BASE/"QA133-FinalDiction"
D.mkdir(parents=True,exist_ok=True)
orig=yaml.safe_load(SRC.read_text(encoding="utf8"))
notes=orig["voice_parts"][0]["notes"]
assert len(notes)==31 and notes[23]["lyric"]=="дождь" and notes[27]["lyric"]=="мою" and notes[28]["lyric"]=="+"
vocab=json.loads((R/"portable"/"Singers"/"Keiro_Revenant_v170"/"files"/"phonemes.json").read_text(encoding="utf8"))
cases={
 "A_native_dosht":{"дождь":["ru/d","ru/o","ru/sh","ru/tj"],"мою":["ru/m","ru/A","ru/j","ru/u"]},
 "B_soft_doshch":{"дождь":["ru/d","ru/o","ru/shj"],"мою":["ru/m","ru/A","ru/j","ru/u"]},
}
for variant,hints in cases.items():
 p=copy.deepcopy(orig)
 c=p["voice_parts"][0]["notes"]
 for word,ph in hints.items():
  assert all(t in vocab for t in ph)
  idx=23 if word=="дождь" else 27
  c[idx]["lyric"]=word+"["+" ".join(ph)+"]"
 p["name"]="HAPYCH QA133 "+variant
 p["comment"]="Test-only explicit phones for Russian rain and 'мою'; no notes/stress/song lyrics altered."
 assert len(c)==31
 for i,(a,b) in enumerate(zip(c,notes)):
  assert {k:v for k,v in a.items() if k!="lyric"}=={k:v for k,v in b.items() if k!="lyric"}
  if i not in (23,27):assert a==b
 for k in ("tracks","tempos","time_signatures","key","resolution"):
  assert p[k]==orig[k],k
 folder=D/variant
 folder.mkdir(exist_ok=True)
 target=folder/"QA133_RussianDiction.ustx"
 target.write_text(yaml.safe_dump(p,allow_unicode=True,sort_keys=False,width=140),encoding="utf8")
 assert yaml.safe_load(target.read_text(encoding="utf8"))["voice_parts"][0]["notes"][27]["lyric"].startswith("мою[ru/m ru/A ru/j ru/u]")
 print("QA133_PREP",variant,target,flush=True)
manifest={"status":"two_variants_prepared","base_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
 "cases":cases,"original_visible_lyrics_unchanged":True,
 "original_timing_and_notes_unchanged":True,
 "production_untouched":True,"license":"LUNAI Project Keiro noncommercial QA only"}
(D/"QA133_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")

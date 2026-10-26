"""QA132: Russian pronunciation correction test in *independent* USTX.
Original visible lyric stays 'Когда' and the only runtime edit is a
RussianG2p explicit hint with weak pretonic a + strong stressed aa.
No singer, note, timing, tempo, key, profile, or production edit.
"""
from pathlib import Path
import yaml,json,hashlib,copy,unicodedata,re,sys
sys.stdout.reconfigure(encoding="utf-8")
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
SRC=R/"QA129_Score"/"QA129_Keiro_RussianDiffSinger.ustx"
OUT=R/"QA132-KogdaPronunciation"
OUT.mkdir(parents=True,exist_ok=True)
proj=yaml.safe_load(SRC.read_text(encoding="utf8"))
assert proj["resolution"]==480 and proj["tempos"]==[{"position":0,"bpm":102}]
assert len(proj["voice_parts"])==1 and len(proj["voice_parts"][0]["notes"])==31
original=copy.deepcopy(proj)
notes=proj["voice_parts"][0]["notes"]
where=[i for i,n in enumerate(notes) if n.get("lyric")=="Когда"]
assert where==[16],where
assert notes[17]["lyric"]=="+" and notes[16]["position"]==8520 and notes[17]["position"]==8940
# In this Keiro-LUNAI dictionary:
# a -> ru/A (reduced Russian [ɐ]), aa -> ru/a (stressed full [a]).
# Other consonants k g d map to ru/k ru/g ru/d.
hint="ru/k ru/A ru/g ru/d ru/a"
dictfile=R/"portable"/"Singers"/"Keiro_Revenant_v170"/"configs"/"dsdur"/"dsdict-ru.yaml"
txt=dictfile.read_text(encoding="utf8")
for expected in ("- {from: a, to: ru/A}", "- {from: aa, to: ru/a}",
                 "- {from: g, to: ru/g}", "- {from: k, to: ru/k}",
                 "- {from: d, to: ru/d}"):
 assert expected in txt,expected
model_phonemes=json.loads((R/"portable"/"Singers"/"Keiro_Revenant_v170"/"files"/"phonemes.json").read_text(encoding="utf8"))
for token in hint.split(): assert token in model_phonemes,token
proj["name"]="HAPYCH QA132 - Kogda spoken vowel reduction"
proj["comment"]="Only QA132 phoneme hint for 'Когда'. Orthographic lyric remains unchanged. Isolated noncommercial audition with Keiro Revenant from LUNAI Project."
notes[16]["lyric"]=f"Когда[{hint}]"
# Validate a single, local, non destructive change of acoustic inputs.
assert [(n["position"],n["duration"],n["tone"],n["pitch"],n["vibrato"])
        for n in notes]==[(n["position"],n["duration"],n["tone"],n["pitch"],n["vibrato"])
        for n in original["voice_parts"][0]["notes"]]
for i,(now,prev) in enumerate(zip(notes,original["voice_parts"][0]["notes"])):
 if i==16:
  old=now["lyric"]
  assert old.startswith(prev["lyric"]+"[") and old.endswith("]")
  assert re.sub(r"\[[^\]]+\]","",old)==prev["lyric"]
 else:
  assert now==prev,(i,now,prev)
assert proj["tracks"]==original["tracks"]
assert proj["key"]==original["key"]
assert proj["tempos"]==original["tempos"]
assert proj["time_signatures"]==original["time_signatures"]
target=OUT/"QA132_Keiro_KogdaReduced.ustx"
target.write_text(yaml.safe_dump(proj,allow_unicode=True,sort_keys=False,width=140),encoding="utf8")
assert yaml.safe_load(target.read_text(encoding="utf8"))["voice_parts"][0]["notes"][16]["lyric"]=="Когда["+hint+"]"
report={
 "purpose":"Fix native Russian unstressed о in 'когда' to spoken vowel; no lyric rewriting",
 "old_ipa":"k o g d a","target_ipa":"k ɐ g d a","target_stress":"[kɐɡˈda]",
 "original_lexeme":"Когда","runtime_lyric_with_hint":"Когда["+hint+"]",
 "lang_mapping":{"pretonic":"ru/A (unstressed approx [ɐ])","stressed":"ru/a (stressed [a])",
   "consonant":"ru/g (voiced, not k)"},"forced_tokens":hint.split(),
 "source_ustx_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
 "new_ustx_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
 "source_audio_preserved":True,"notes_unchanged":True,"tempo_unchanged":True,
 "singer_unchanged":True,"owner_voice_unchanged":True,
 "runtime_audio_generated":False,"listening_confirmed":False,
 "not_for_production":True,"license":"Noncommercial control only, Keiro Revenant from LUNAI Project"}
(OUT/"QA132_manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("QA132_PHONEME_HINT_VALID",report["runtime_lyric_with_hint"],"ORIG_ORTHOGRAPHY",report["original_lexeme"])
print("QA132_PROJECT",target)

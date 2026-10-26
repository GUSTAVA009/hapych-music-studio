"""QA132 case-safe G2P patch for Keiro DiffSinger, no source lyrics changed.
Produces an isolated USTX with explicit phoneme hints only when the real
OpenUtau RussianG2p's capitalized word disagrees with lowercase prediction.
The source project and voicebank remain unmodified.
"""
from pathlib import Path
import json,yaml,copy,re,hashlib,sys
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
S=R/"QA129_Score"/"QA129_Keiro_RussianDiffSinger.ustx"
D=R/"QA132-KogdaPronunciation"
cases=json.loads((D/"QA132_g2p_case_results.json").read_text(encoding="utf8"))
assert cases["status"]=="case_pair_verified" and cases["entries"]==17
assert cases["mismatches"]==2
model=R/"portable"/"Singers"/"Keiro_Revenant_v170"
dict_data=yaml.safe_load((model/"configs"/"dsdur"/"dsdict-ru.yaml").read_text(encoding="utf8"))
replacements={x["from"]:x["to"] for x in dict_data["replacements"]}
vocab=json.loads((model/"files"/"phonemes.json").read_text(encoding="utf8"))
def tokens(seq):
 out=[]
 for phoneme in seq:
  v=replacements.get(phoneme)
  if v is None:v="ru/"+phoneme
  if v not in vocab:raise ValueError(f"Unknown Keiro phoneme {phoneme}->{v}")
  out.append(v)
 assert len(out)==len(seq)
 return out
model_cases={p["Word"]:p for p in cases["cases"]}
doc=yaml.safe_load(S.read_text(encoding="utf8"))
source=copy.deepcopy(doc)
notes=doc["voice_parts"][0]["notes"]
changes=[]
for i,n in enumerate(notes):
 raw=n["lyric"]
 if raw in ("+","-"):continue
 row=model_cases[raw]
 if not row["Differ"]:continue
 assert raw[0].isupper() and raw.lower()!=raw
 phonemes=tokens(row["LowerCase"])
 hint=" ".join(phonemes)
 n["lyric"]=f"{raw}[{hint}]"
 changes.append({
  "note_index":i,"original_word":raw,"spoken_word":raw.lower(),
  "wrong_case_g2p":row["OriginalCase"],
  "correct_normalized_g2p":row["LowerCase"],
  "forced_model_phonemes":phonemes,
  "saved_lyric":n["lyric"]})
assert len(changes)==2,changes
assert {x["original_word"] for x in changes}=={"Мне","Когда"},changes
assert [x["position"] for x in notes]==[x["position"] for x in source["voice_parts"][0]["notes"]]
assert [x["duration"] for x in notes]==[x["duration"] for x in source["voice_parts"][0]["notes"]]
assert [x["tone"] for x in notes]==[x["tone"] for x in source["voice_parts"][0]["notes"]]
for i,(a,b) in enumerate(zip(notes,source["voice_parts"][0]["notes"])):
 if a!=b:
  assert a.keys()==b.keys()
  assert {k:v for k,v in a.items() if k!="lyric"}=={k:v for k,v in b.items() if k!="lyric"},i
  assert re.sub(r"\[[^\]]+\]","",a["lyric"])==b["lyric"],i
assert doc["tracks"]==source["tracks"]
assert doc["time_signatures"]==source["time_signatures"]
assert doc["tempos"]==source["tempos"]
assert doc["key"]==source["key"]
doc["name"]="HAPYCH QA132 - Case corrected Russian G2P"
doc["comment"]="Phonetic hints for capitalized words only when RussianG2p differs from lowercase; original written lyrics unchanged."
output=D/"QA132_Keiro_RussianCaseGuard.ustx"
output.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=120),encoding="utf8")
restored=yaml.safe_load(output.read_text(encoding="utf8"))
assert restored["voice_parts"][0]["notes"][0]["lyric"]=="Мне[ru/m ru/nj ru/e]"
assert restored["voice_parts"][0]["notes"][16]["lyric"]=="Когда[ru/k ru/A ru/g ru/d ru/a]"
assert len(restored["voice_parts"][0]["notes"])==31
# Sidecar is now aligned with our intended Russian reduction; unchanged
# earlier source audio remains the baseline and is not rewritten.
baseline=json.loads((R/"QA129_Score"/"QA129_phones.json").read_text(encoding="utf8"))
corrected=copy.deepcopy(baseline)
for item in corrected["syllables"]:
 if item["word"]=="Когда" and item["syllable"]=="Ког":
  assert item["phonemes_ipa"]==["k","o"],item
  item["phonemes_ipa"]=["k","ɐ"]
  item["qa132_case_correction"]="unstressed o -> strong pretonic ɐ"
corrected["status"]="QA132_phonetic_metadata_corrected_only"
corrected["notes_and_timing_unchanged"]=True
corrected["audio_generated"]=False
(D/"QA132_corrected_ipa.json").write_text(json.dumps(corrected,ensure_ascii=False,indent=2),encoding="utf8")
report={
 "status":"case_guard_ustx_and_phonemes_created",
 "g2p_engine":"OpenUtau-LUNAI RussianG2p real CPU inference, observed case mismatch",
 "original_song_writing_preserved":True,
 "changes":changes,
 "other_15_words_untouched":True,
 "source_ustx_sha256":hashlib.sha256(S.read_bytes()).hexdigest(),
 "output_ustx_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "voicebank_files_unchanged":True,
 "user_recordings_unchanged":True,
 "not_installed_in_music_studio":True,
 "audio_generated":False,
 "audio_checked_by_human":False,
 "test_project":str(output),
 "warning":"This is a verified phoneme-level correction, not an audio result. Do not claim sound fixed until new render is heard.",
 "license":"Non-commercial audition only; Keiro Revenant from LUNAI Project."}
(D/"QA132_caseguard_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("QA132_CASE_GUARD_PASS",len(changes),"FIXED",[(x["original_word"],x["forced_model_phonemes"]) for x in changes],flush=True)
print("QA132_WRITTEN",output,flush=True)

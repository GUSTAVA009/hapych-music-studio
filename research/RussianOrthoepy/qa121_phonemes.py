"""Stage 2: IPA phonemes and context-sensitive allophones for QA121.
This module is a text-side control validator, not an audio synthesizer.
Runs in separate RuTranscript venv. Saves a machine-readable sidecar and QA.
"""
from pathlib import Path
import json,re,sys,os,hashlib,unicodedata
ROOT=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"
IN=Path(os.environ.get("HAPYCH_STRESS_JSON",str(ROOT/"QA121_orthoepy_stress.json")))
OUT=Path(os.environ.get("HAPYCH_IPA_JSON",str(ROOT/"QA121_orthoepy_ipa.json")))
NOTE=Path(os.environ.get("HAPYCH_IPA_REVIEW",str(ROOT/"QA121_orthoepy_review.txt")))
from ru_transcript import RuTranscript
doc=json.loads(IN.read_text(encoding="utf8"))
VOWELS="аеёиоуыэюя"
def extract_syllables(s):
 return sum(ch.lower() in VOWELS for ch in s)
def phone_diagnostics(ipa:list[str])->dict:
 vals=[p for p in ipa if p not in ("_","+","|","||")]
 return {
  "has_palatals":any("ʲ" in p or "ᶣ" in p for p in vals),
  "has_sibilants":any("ʂ" in p or "ɕ" in p for p in vals),
  "phoneme_count":len(vals),
  "ipa_phones":vals,
 }
lines=[]
for row in doc["lines"]:
 s=row["literal_lyrics"]
 marked=row["reviewed_stress_for_phonemes"]
 assert s.replace(" ","").replace(",","").replace(".","")==marked.replace("+","").replace(" ","").replace(",","").replace(".",""),(s,marked)
 # reviewed accent string marks a stressed vowel with "+" directly BEFORE it.
 tr=RuTranscript(s,marked,stress_place="before")
 tr.transcribe()
 ph=tr.get_phonemes(save_stresses=True,save_spaces=True)
 allo=tr.get_allophones(save_stresses=True,save_spaces=True)
 normalized=tr.get_stressed_text()
 item={"literal_lyrics":s,"phoneme_notation":"IPA",
       "normalized_pronunciation":normalized,
       "reviewed_stress":marked,
       "phonemes":ph,"allophones":allo,
       "phonemes_string":" ".join(ph),
       "syllable_count_orthographic":extract_syllables(s),
       "phones":phone_diagnostics(ph),
       "speaking_vs_singing_warning":"No phoneme-to-note durations computed",
       "automatic_orthoepy_not_100_percent_reliable":True}
 lines.append(item)
 print("QA121_IPA_LINE",json.dumps({"line":s,"stress":marked,
  "phonemes":" ".join(ph),"allophones":" ".join(allo),
  "syllable_count":item["syllable_count_orthographic"]},
  ensure_ascii=False),flush=True)
# Verify that high-priority corrected "окон" is not stressed on final vowel.
if any("окон" in r["literal_lyrics"] for r in lines):
 assert any("+окон" in r["reviewed_stress"] for r in lines)
assert all("ок+он" not in r["reviewed_stress"] for r in lines)
# At least one instance each of critical words was processed as Russian IPA.
if "qa119_generation.json" in str(doc["source"]).lower():
 for term in ("мне","услышишь","поймёшь","найдёшь","дождь","окон"):
  assert any(term in row["literal_lyrics"].lower() for row in lines),term
out={"module":"HAPYCH-Orthoepy QA121",
 "phoneme_backend":"RuTranscript 2.2.0",
 "accent_backend":"RUAccent tiny + manually checked exceptions",
 "source_sha256":hashlib.sha256(IN.read_bytes()).hexdigest(),
 "word_stress_controls_reached_g2p":True,
 "current_ACE_does_NOT_consume_IPA":True,
 "exact_note_alignment_supported":False,
 "singing_timbre_model_changed":False,
 "new_song_rendered":False,
 "qa":lines}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
candidates="\n".join(f"{i+1:02d}. {x['literal_lyrics']}\n    Accent: {x['reviewed_stress']}\n    IPA: {x['phonemes_string']}"
 for i,x in enumerate(lines))
NOTE.write_text("QA121 RUSSIAN ORTHOEPY - TEXT-SIDE VALIDATION ONLY\n"
 "RUAccent suggested stress + dictionary override; RuTranscript provided IPA.\n"
 "Dictionary correction when applicable: genitive plural +okon, not ok+on.\n"
 "Do not paste +accent markers or IPA into the current ACE-Step lyric input.\n"
 "No singing/audio generated; no change in timbre or accent is claimed.\n\n"+
 candidates+"\n",encoding="utf8")
print("QA121_IPA_SIDECAR_READY",str(OUT),"LINES",len(lines),flush=True)

"""Russian orthoepic audit for HAPYCH Music Studio (isolated prototype).

It validates stress/palatalization requirements as sidecar metadata.
It deliberately NEVER substitutes pronunciations for the ACE-Step lyrics
because ACE-Step 1.5 lacks a phoneme-aware lyric input. This is a QA aid,
NOT a G2P engine and NOT a speech-quality improvement by itself.
"""
from __future__ import annotations
import argparse,json,re,unicodedata,sys
sys.stdout.reconfigure(encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56))
from pathlib import Path

# Human-curated stress and articulation cues for words repeatedly
# damaged by ACE-Step/SoulX/Seed-VC. 0-based stress vowel ordinal.
LEXICON={
 "мне":{"stressed_vowel":0,"stressed_form":"мне",
  "articulation":["soft_n_before_e"],"critical":"Never make н hard: not мнэ"},
 "услышишь":{"stressed_vowel":1,"stressed_form":"услы́шишь",
  "articulation":["preserve_ы_under_stress","retain_full_шишь_ending"],
  "critical":"Not услышащий, and stress must stay on ы"},
 "поймёшь":{"stressed_vowel":1,"stressed_form":"поймёшь",
  "articulation":["preserve_yo","retain_full_шь_ending"],
  "critical":"Keep ё and the ending, no accent on first vowel"},
 "найдёшь":{"stressed_vowel":1,"stressed_form":"найдёшь",
  "articulation":["preserve_yo","retain_full_шь_ending"],
  "critical":"Keep stressed ё and word ending"},
 "дождь":{"stressed_vowel":0,"stressed_form":"до́ждь",
  "articulation":["native_ждь_cluster","avoid_foreign_dzh"],
  "critical":"Native Russian cluster; do not pronounce letter-by-letter"},
 "вечер":{"stressed_vowel":0,"stressed_form":"ве́чер",
  "articulation":["clear_ч","unstressed_second_vowel"],
  "critical":"Avoid phonemic gaps between syllables"},
 "окон":{"stressed_vowel":0,"stressed_form":"о́кон",
  "articulation":["initial_stress","unstressed_second_o"],
  "critical":"The second о is unstressed"},
 "ответ":{"stressed_vowel":1,"stressed_form":"отве́т",
  "articulation":["unstressed_initial_o","retain_final_т"],
  "critical":"Final consonant must remain audible"},
 "ждёшь":{"stressed_vowel":0,"stressed_form":"ждёшь",
  "articulation":["preserve_yo","native_жд_cluster"],
  "critical":"Stressed ё, keep complete final шь"},
 "свет":{"stressed_vowel":0,"stressed_form":"свет",
  "articulation":["soft_в_before_e","final_т_intact"],
  "critical":"Do not truncate final т"}
}
VOWELS="аеёиоуыэюя"
TOKENS=re.compile(r"[а-яё]+",re.I)
TAG=re.compile(r"\[[^\]]+\]")
def clean_stress(text:str)->str:
    # Do not erase U+0308 ('ё') as generic accent removal might.
    return unicodedata.normalize("NFC",text.replace("\u0301",""))
def content_words(lyrics:str)->list[str]:
    plain=TAG.sub(" ",lyrics)
    return TOKENS.findall(clean_stress(plain.lower()))
def marked_index(word:str)->int|None:
    # Check stress accent in original. The rune may follow 'ы', 'а' etc.
    s=unicodedata.normalize("NFC",word)
    pos=s.find("\u0301")
    if pos<0:return None
    previous=s[:pos]
    if not previous or previous[-1].lower() not in VOWELS:return -1
    return sum(ch in VOWELS for ch in previous.lower())-1
def audit(lyrics:str, *, original_case:str="test")->dict:
    words=content_words(lyrics)
    annotated=[]
    seen=set()
    for token in words:
        k=token.lower()
        if k not in LEXICON:continue
        obj=LEXICON[k]
        annotated.append({"word":k,"stressed_form":obj["stressed_form"],
          "stress_vowel_index_0based":obj["stressed_vowel"],
          "pronunciation_constraints":obj["articulation"],
          "attention":obj["critical"]})
        seen.add(k)
    # Flag explicit stress marks in the *original* lyrics.
    # The QA120 test found such markup may worsen ACE-Step performance.
    tagged_removed=TAG.sub(" ",unicodedata.normalize("NFC",lyrics))
    unusual_stress="\u0301" in tagged_removed
    if unusual_stress:
        all_tokens=re.findall(r"[а-яё\u0301]+",tagged_removed.lower())
        stress_details=[{"token":x,"stress_index":marked_index(x)}
                        for x in all_tokens if "\u0301" in x]
    else:stress_details=[]
    return {"source":original_case,"total_word_tokens":len(words),
     "curated_words_found":len(annotated),
     "curated_word_types":sorted(seen),
     "word_constraints":annotated,
     "has_visible_stress_marks":unusual_stress,
     "explicit_stress_marks":stress_details,
     "raw_lyrics_should_be_preserved":True,
     "phonetic_sidecar_to_vocal_model_only":True,
     "ACE_Step_1_5_accepts_phoneme_alignment":False,
     "automatic_stress_for_unknown_homographs":False,
     "improved_audio_generated":False,
     "no_user_recordings_used":True}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("lyrics_json",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    ns=parser.parse_args()
    data=json.loads(ns.lyrics_json.read_text(encoding="utf8"))
    lyrics=data.get("lyrics")
    assert isinstance(lyrics,str) and lyrics.strip()
    result=audit(lyrics,original_case=ns.lyrics_json.name)
    assert result["curated_words_found"]>=5
    ns.output.parent.mkdir(exist_ok=True,parents=True)
    ns.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("ORTHOEPY_AUDIT",json.dumps(
      {k:v for k,v in result.items() if k!="word_constraints"},
      ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()

"""QA129: isolated Russian syllable / IPA / note score compiler.
Produces a native OpenUtau USTX score, MIDI guide and a phoneme-duration sidecar.
No singing is synthesized here; voicebank phoneme inventories must be validated separately.
Never edits production Music Studio or personal microphone recordings.
"""
from pathlib import Path
from ru_transcript import RuTranscript
import json, csv, io, math, struct, sys, hashlib
import yaml
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path.home()/"Music Studio"
OUT=ROOT/"Integrations"/"OpenUtau-QA129"/"QA129_Score"
OUT.mkdir(parents=True,exist_ok=True)
VOWELS={"a","e","i","o","u","ɨ","ə","ɐ","ɛ","ɪ","ʊ","ɵ","y","ʉ"}
BPM=102
TICKS_PER_BEAT=480
CASES=[
 {"text":"Мне нужен свет твоих окон.",
  "marked":"Мн+е н+ужен св+ет тво+их +окон.",
  "words":[["Мне"],["ну","жен"],["свет"],["тво","их"],["о","кон"]],
  "stress":[0,1,3,5,6],
  "pitches":[46,48,50,48,50,53,50,46]},
 {"text":"Меня услышишь и поймёшь.",
  "marked":"Мен+я усл+ышишь и поймёшь.",
  "words":[["Ме","ня"],["у","слы","шишь"],["и"],["пой","мёшь"]],
  "stress":[1,3,7],
  "pitches":[46,48,50,53,50,48,50,46]},
 {"text":"Когда за окном идёт дождь.",
  "marked":"Когд+а з+а окн+ом идёт д+ождь.",
  "words":[["Ког","да"],["за"],["ок","ном"],["и","дёт"],["дождь"]],
  "stress":[1,2,4,6,7],
  "pitches":[43,46,48,46,50,48,46,43]},
 {"text":"Сохрани мою любовь.",
  "marked":"Сохран+и мо+ю люб+овь.",
  "words":[["Со","хра","ни"],["мо","ю"],["лю","бовь"]],
  "stress":[2,4,6],
  "pitches":[43,46,48,50,48,46,43]},
]
def only_words(s):
 import re
 return re.findall(r"[А-Яа-яЁё]+",s)
def extract_word_phones(text,marked):
 import re
 raw_words=only_words(text)
 accent_words=re.findall(r"[+А-Яа-яЁё]+",marked)
 assert len(raw_words)==len(accent_words),(text,marked)
 groups=[]
 # RuTranscript merges adjacent words under coarticulation; individual word
 # calls keep note boundaries unambiguous. Preserve full-line IPA separately.
 for raw, accent in zip(raw_words,accent_words):
  assert raw.lower()==accent.replace("+","").lower(),(raw,accent)
  tr=RuTranscript(raw,accent,stress_place="before")
  tr.transcribe()
  groups.append([p for p in tr.get_phonemes(save_stresses=True,save_spaces=False) if p not in ("_","|","||")])
 return groups
def split_phone_syllables(group):
 nuclei=[j for j,p in enumerate(group) if p in VOWELS]
 if not nuclei: raise ValueError("No IPA vowel: "+str(group))
 bounds=[0]+[j+1 for j in nuclei[:-1]]+[len(group)]
 sylls=[group[bounds[i]:bounds[i+1]] for i in range(len(bounds)-1)]
 assert len(sylls)==len(nuclei),sylls
 assert all(sum(p in VOWELS for p in syl)==1 for syl in sylls),sylls
 return sylls
def midi_vlq(n):
 assert n>=0
 b=[n&0x7f];n>>=7
 while n:b.insert(0,(n&0x7f)|0x80);n>>=7
 return bytes(b)
def midi_event_delta(prev,ts,data):
 return midi_vlq(ts-prev)+data
syllables=[];notes=[];tick=0
for li,row in enumerate(CASES):
 words=only_words(row["text"])
 groups=extract_word_phones(row["text"],row["marked"])
 assert len(groups)==len(words),(row["text"],words,groups)
 assert len(row["pitches"])==sum(len(a) for a in row["words"])
 assert set(row["stress"]) <= set(range(sum(len(a) for a in row["words"])))
 assert len(row["stress"])>0
 assert tick>=0
 counter=0
 for wi,(word,labels,phonemes) in enumerate(zip(words,row["words"],groups)):
  assert len(labels)>0
  assert "".join(labels).casefold()==word.casefold(),(word,labels)
  phone_syls=split_phone_syllables(phonemes)
  assert len(phone_syls)==len(labels),(word,labels,phone_syls)
  for si,(label,ph) in enumerate(zip(labels,phone_syls)):
   stressed=counter in row["stress"]
   from_ipa=("+" in ph) or ("ё" in label.lower())
   # Some monosyllabic function words have no lexical stress in context.
   if len(labels)>1:
    assert stressed==from_ipa,(word,label,ph,stressed,from_ipa)
   duration=540 if stressed else 420
   if label.lower() in ("и","за") and not stressed:duration=300
   if li==3 and counter==6:duration=960 # keep final stressed "бо́вь" continuous
   phone_items=[v for v in ph if v!="+"]
   total_ms=round(duration*60000/(BPM*TICKS_PER_BEAT),2)
   vindex=next(j for j,x in enumerate(phone_items) if x in VOWELS)
   ncons=len(phone_items)-1
   vowel_share=0.76 if stressed else 0.60
   # Allocate time to the vowel nucleus; consonants retain a real, finite window.
   vowel_ms=round(total_ms*vowel_share,2)
   cons_ms=round((total_ms-vowel_ms)/ncons,2) if ncons else 0.0
   durations=[vowel_ms if j==vindex else cons_ms for j in range(len(phone_items))]
   if ncons:durations[-1]=round(total_ms-sum(durations[:-1]),2)
   notes.append({"position":tick,"duration":duration,"tone":row["pitches"][counter],
       "lyric":label,
       "pitch":{"data":[{"x":-40,"y":0,"shape":"io"},{"x":40,"y":0,"shape":"io"}],"snap_first":True},
       "vibrato":{"length":0,"period":175,"depth":0,"in":10,"out":10,"shift":0,"drift":0,"vol_link":0},
       "phoneme_expressions":[],"phoneme_overrides":[]})
   syllables.append({"line":li+1,"word":word,"syllable":label,"word_index":wi+1,
       "note_index":counter+1,"tick":tick,"duration_ticks":duration,"duration_ms":total_ms,
       "midi_note":row["pitches"][counter],"stressed":stressed,
       "phonemes_ipa":phone_items,"phoneme_durations_ms":durations,
       "ipa_stress_found":from_ipa,
       "vowel_index":vindex})
   tick+=duration;counter+=1
 assert counter==len(row["pitches"])
 tick+=480 # full 102-BPM beat of breath before the next phrase
 assert "".join("".join(s) for s in row["words"]).lower() == "".join(words).lower()
total_ticks=tick
project={
 "name":"HAPYCH QA129 - Russian phoneme melody proof",
 "comment":"Phonemes and stresses in QA129_phones.json. No trained owner singer installed.",
 "output_dir":"Export","cache_dir":"UCache","ustx_version":"0.6",
 "resolution":480,"key":5,
 "time_signatures":[{"bar_position":0,"beat_per_bar":4,"beat_unit":4}],
 "tempos":[{"position":0,"bpm":BPM}],
 "tracks":[{"singer":"","phonemizer":"OpenUtau.Core.DefaultPhonemizer",
  "renderer_settings":{},"track_name":"Русские слоги — низкий баритон (нет вокалиста)",
  "track_color":"Blue","mute":False,"solo":False,"volume":0.0,"pan":0.0,
  "voice_color_names":[""]}],
 "voice_parts":[{"name":"4 фразы — фонемная проверка","comment":"Контроль о́кон / услы́шишь / дождь / сохрани́",
  "track_no":0,"position":0,"duration":total_ticks,"notes":notes,"curves":[]}],
 "wave_parts":[]}
project_file=OUT/"QA129_RussianPhonemeScore.ustx"
project_file.write_text(yaml.safe_dump(project,allow_unicode=True,sort_keys=False,width=120),encoding="utf-8")
with (OUT/"QA129_note_sheet.csv").open("w",encoding="utf-8-sig",newline="") as f:
 keys=["line","word","syllable","tick","duration_ticks","duration_ms","midi_note","stressed","phonemes_ipa"]
 w=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore");w.writeheader()
 for s in syllables:
  t=dict(s);t["phonemes_ipa"]=" ".join(s["phonemes_ipa"]);w.writerow(t)
# A minimal standard MIDI with track-one note/lyric events. Musical timing can be inspected.
tempo=round(60000000/BPM)
ev=[(0,b"\xff\x51\x03"+tempo.to_bytes(3,"big"))]
for x in syllables:
 tm=x["tick"];pitch=x["midi_note"];vel=88 if x["stressed"] else 74
 lyric=x["syllable"].encode("utf-8")
 ev.append((tm,b"\xff\x05"+midi_vlq(len(lyric))+lyric))
 ev.append((tm,bytes([0x90,pitch,vel])))
 ev.append((tm+x["duration_ticks"],bytes([0x80,pitch,0])))
ev.sort(key=lambda a:(a[0],0 if a[1][:1]==b"\x80" else 1))
data=bytearray();last=0
for when,payload in ev:
 data.extend(midi_event_delta(last,when,payload));last=when
data.extend(b"\x00\xff\x2f\x00")
smf=b"MThd"+struct.pack(">IHHH",6,0,1,TICKS_PER_BEAT)+b"MTrk"+struct.pack(">I",len(data))+data
(OUT/"QA129_RussianPhonemeScore.mid").write_bytes(smf)
report={
 "status":"phoneme_note_score_ready; no voicebank acoustic rendering",
 "lines":len(CASES),"notes":len(notes),"ipa_phones":sum(len(s["phonemes_ipa"]) for s in syllables),
 "stressed_syllables":sum(s["stressed"] for s in syllables),
 "duration_sec":round(total_ticks*60/(BPM*TICKS_PER_BEAT),2),
 "no_voice_training":True,"no_audio_generated":True,"production_modified":False,
 "no_phoneme_map_to_voicebank_yet":True,"user_voice_samples_untouched":True,
 "limitations":"IPA note schedule must be mapped to specific model phoneme inventory; MIDI is only a guide, not a synthesized voice",
 "input_lines":[c["text"] for c in CASES],"syllables":syllables}
(OUT/"QA129_phones.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA129_SCORE_PASS",json.dumps({k:report[k] for k in ("lines","notes","ipa_phones","stressed_syllables","duration_sec")},ensure_ascii=False))
print("QA129_FILES",project_file,OUT/"QA129_RussianPhonemeScore.mid",OUT/"QA129_phones.json")

"""Stage 1 of QA121: context-sensitive automatic stress + reviewed overrides.
Only outputs metadata, not lyrics submitted to ACE or audio.
Runs in isolated RUAccent environment. Models already downloaded.
"""
from pathlib import Path
import json,re,sys,os,unicodedata,time
ROOT=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"
SOURCE=Path(os.environ.get("HAPYCH_SOURCE_JSON", str(Path.home()/"Music Studio"/"Diagnostics"/"QA119-RussianDiction"/"qa119_generation.json")))
OUT=Path(os.environ.get("HAPYCH_STRESS_JSON",str(ROOT/"QA121_orthoepy_stress.json")))
from ruaccent import RUAccent
accent=RUAccent()
t=time.monotonic()
accent.load(omograph_model_size="tiny",use_dictionary=True,
 device="CPU",tiny_mode=False,workdir=str(ROOT/"models"))
print("QA121_ACCENT_MODEL_LOADED_SECONDS",round(time.monotonic()-t,2),flush=True)
data=json.loads(SOURCE.read_text(encoding="utf8"))
lines=[p.strip() for p in data["lyrics"].splitlines() if p.strip() and not p.startswith("[")]
# Applied AFTER model prediction. The strong stress form is verified in
# the Russian Academy-backed normative dictionary: gramota.ru/meta/okno.
OVERRIDES={
 "окон":"+окон",  # gen.pl. ókon, not *okón.
 "услышишь":"усл+ышишь",
 "поймёшь":"поймёшь",  # ё carries lexical stress.
 "найдёшь":"найдёшь",
 "дождь":"д+ождь",
}
TOKEN=re.compile(r"[+а-яё]+",re.I)
def plain(token):
 return unicodedata.normalize("NFC",token.replace("+","").replace("\u0301","").lower())
def override(annotated):
 spans=[];applied=[]
 for m in TOKEN.finditer(annotated):
  word=m.group()
  lex=plain(word)
  if lex in OVERRIDES:
   replacement=OVERRIDES[lex]
   if word!=replacement:
    applied.append({"word":lex,"predicted":word,"forced":replacement,
                    "reason":"reviewed_Russian_orthoepy"})
   spans.append(replacement)
  else:spans.append(word)
 # preserve punctuation and whitespace exactly, not by token concatenation.
 result=TOKEN.sub(lambda m:OVERRIDES.get(plain(m.group()),m.group()),annotated)
 return result,applied
out=[]
for n,line in enumerate(lines):
 automatic=accent.process_all(line)
 reviewed,changes=override(automatic)
 assert plain(reviewed.replace(" ",""))==plain(line.replace(" ","")), (line,reviewed)
 out.append({"line_number":n+1,"literal_lyrics":line,
  "ruaccent_suggestion":automatic,
  "reviewed_stress_for_phonemes":reviewed,"changes":changes,
  "unresolved_phonetic_exceptions":"Requires human ear verification"})
 print("QA121_STRESS",json.dumps({"line":line,"suggestion":automatic,
  "reviewed":reviewed,"overrides":changes},ensure_ascii=False),flush=True)
doc={"source":str(SOURCE),"provider":"RUAccent 1.5.8.3 tiny CPU + reviewed overrides",
 "normative_override_for_окон":"https://gramota.ru/meta/okno",
 "notes":["No stress mark is inserted into ACE-Step lyrics",
          "Models can place stress incorrectly; compare against dictionaries",
          "Prosody and timing are not synthesized or aligned here"],
 "original_lyrics_untouched":True,"lines":out}
OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf8")
print("QA121_STRESS_SIDECAR_READY",str(OUT),flush=True)

"""Make the verified QA121 stress/G2P prototypes reusable for any lyrics JSON.
Original QA119 and QA121 artifacts remain untouched.
"""
from pathlib import Path
R=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"
p=R/"qa121_stress.py"
s=p.read_text(encoding="utf8")
assert 'import json,re,sys,unicodedata,time' in s
s=s.replace('import json,re,sys,unicodedata,time','import json,re,sys,os,unicodedata,time')
old='SOURCE=Path.home()/"Music Studio"/"Diagnostics"/"QA119-RussianDiction"/"qa119_generation.json"'
new='SOURCE=Path(os.environ.get("HAPYCH_SOURCE_JSON", str(Path.home()/"Music Studio"/"Diagnostics"/"QA119-RussianDiction"/"qa119_generation.json")))'
assert old in s;s=s.replace(old,new)
old='OUT=ROOT/"QA121_orthoepy_stress.json"'
new='OUT=Path(os.environ.get("HAPYCH_STRESS_JSON",str(ROOT/"QA121_orthoepy_stress.json")))'
assert old in s;s=s.replace(old,new)
p.write_text(s,encoding="utf8")
q=R/"qa121_phonemes.py"
s=q.read_text(encoding="utf8")
assert 'import json,re,sys,hashlib,unicodedata' in s
s=s.replace('import json,re,sys,hashlib,unicodedata','import json,re,sys,os,hashlib,unicodedata')
pairs=[
 ('IN=ROOT/"QA121_orthoepy_stress.json"','IN=Path(os.environ.get("HAPYCH_STRESS_JSON",str(ROOT/"QA121_orthoepy_stress.json")))'),
 ('OUT=ROOT/"QA121_orthoepy_ipa.json"','OUT=Path(os.environ.get("HAPYCH_IPA_JSON",str(ROOT/"QA121_orthoepy_ipa.json")))'),
 ('NOTE=ROOT/"QA121_orthoepy_review.txt"','NOTE=Path(os.environ.get("HAPYCH_IPA_REVIEW",str(ROOT/"QA121_orthoepy_review.txt")))')]
for old,new in pairs:
 assert old in s,old;s=s.replace(old,new)
s=s.replace('assert any("+окон" in r["reviewed_stress"] for r in lines)',
 'if any("окон" in r["literal_lyrics"] for r in lines):\n assert any("+окон" in r["reviewed_stress"] for r in lines)')
s=s.replace('for term in ("мне","услышишь","поймёшь","найдёшь","дождь","окон"):\n assert any(term in row["literal_lyrics"].lower() for row in lines),term',
 'if "qa119_generation.json" in str(doc["source"]).lower():\n for term in ("мне","услышишь","поймёшь","найдёшь","дождь","окон"):\n  assert any(term in row["literal_lyrics"].lower() for row in lines),term')
s=s.replace('"Important correction: plural genitive \'o-kon\' is stressed FIRST o: +okon, not ok+on.\\n"','"Dictionary correction when applicable: genitive plural +okon, not ok+on.\\n"')
q.write_text(s,encoding="utf8")
print("QA121_REUSABLE_SCRIPTS_PATCHED")

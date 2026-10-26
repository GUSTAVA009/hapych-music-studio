import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from studio_sections import prepare_request
from sound_effects29 import planned_effects
root=Path.home()/"Music Studio"/"Мои тексты"
ly=(root/"День сурка - полный сценарий SFX.txt").read_text(encoding="utf-8")
st=(root/"День сурка - стиль и промпт.txt").read_text(encoding="utf-8")
p=prepare_request({"lyrics":ly,"style":st,"vocal_language":"ru","vocal_gender":"male"})
e=planned_effects(p["sections"])
print("raw chars",len(ly),"prepared ACE lyrics chars",len(p["lyrics"]),"plain ACE lyrics chars",len(p["plain_lyrics"]))
print("sections",len(p["sections"]),"effect requests",len(e),"supported",sum(x["supported"] for x in e))
print("not supported",[x["requested"] for x in e if not x["supported"]])
print("reported warnings",p["warnings"][-4:])
assert len(p["lyrics"])<=4096
assert len(e)>=25
assert not any("[SFX:" in x["lyrics"] for x in p["sections"])
print("USER FULL SCRIPT PREPARE PASS")

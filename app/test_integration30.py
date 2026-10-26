from pathlib import Path
import sys
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
import studio_server
from sound_effects29 import planned_effects
from sound_catalog30 import stats
root=Path.home()/"Music Studio"/"Мои тексты"
ly=(root/"День сурка - полный сценарий SFX.txt").read_text(encoding="utf-8")
st=(root/"День сурка - стиль и промпт.txt").read_text(encoding="utf-8")
p=studio_server.prepare_request({"lyrics":ly,"style":st,"bpm":92,"duration":300,"vocal_language":"auto"})
print("USER ORIGINAL",len(st),"MODEL CAPTION",len(p["caption"]),p["caption"])
print("DETECTED SFX",len(p["effects_plan"]),"SUPPORTED",sum(x["supported"] for x in p["effects_plan"]))
print("OMITTED",p["style_plan"]["not_sent_to_model"])
print("STYLEFX",p.get("style_sfx_added"))
print("UNSUPPORTED",[(x["effect"],x["requested"]) for x in p["effects_plan"] if not x["supported"]])
assert p["style_plan"]["prompt_compiler"]=="loss_aware_style30"
assert len(p["caption"])<=512
assert "4 male backing" in p["caption"]
assert "saxophone" in p["caption"]
assert "piano" in p["caption"]
assert sum(x["supported"] for x in p["effects_plan"])==len(p["effects_plan"])
assert "SFX:" not in p["lyrics"]
assert p["music_key"]=="D minor"
sty="Cinematic urban noir, heavy piano and strings, Russian male baritone, 102 BPM, D minor. SFX: thunder, car engine starts, coins dropping, rain"
inp={"style":sty,"lyrics":"[Intro]\nЯ снова здесь\n[Verse]\nНочь на районе","vocal_language":"auto"}
p2=studio_server.prepare_request(inp)
print("STYLE ONLY SFX",p2["style_sfx_added"])
print("STYLE ONLY EFFECTS",[(a["effect"],a["supported"]) for a in p2["effects_plan"]])
assert len(p2["effects_plan"])==4
assert all(a["supported"] for a in p2["effects_plan"])
assert "102 BPM" in p2["caption"]
assert len(p2["caption"])<=512
print("INTEGRATION PASS",stats()["total_imported_audio"],"audios")

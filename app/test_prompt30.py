import sys
from pathlib import Path
p=Path(__file__).resolve().parent;sys.path.insert(0,str(p))
from studio_sections import prepare_request as section_prepare
from prompt_director30 import compile_brief
root=Path.home()/"Music Studio"/"Мои тексты"
raw=(root/"День сурка - стиль и промпт.txt").read_text(encoding="utf-8")
prepared=section_prepare({"lyrics":(root/"День сурка - полный сценарий SFX.txt").read_text(encoding="utf-8"),"style":raw})
old=prepared["caption"]
p=compile_brief(raw,prepared)
print("original raw chars",len(raw))
print("old preprocess len",len(old))
print("new model caption",p["caption"])
print("new len",len(p["caption"]))
print("kept",p["style_plan"]["kept_directions"])
print("not_sent",p["style_plan"]["not_sent_to_model"])
assert len(p["caption"])<=512
for k in ("piano","strings","saxophone","guitar","808","Russian","baritone"):
    assert k.lower() in p["caption"].lower(),k
print("SUCCESS original brief")
long=raw+"; " + "; ".join(["spacious environmental ambience","wide layered background vocals","organic live bass","specific dark crime noir attack","melancholic analog piano reverb","delicate late-night woodwinds","rich urban soundscapes"]*5)
p2=compile_brief(long,prepared)
print("LONG",len(long),len(p2["caption"]),"preserved",p2["style_plan"]["complete_style_source"]==long,"dropped",len(p2["style_plan"]["not_sent_to_model"]))
assert len(p2["caption"])<=512
assert len(p2["style_plan"]["complete_style_source"])==len(long)

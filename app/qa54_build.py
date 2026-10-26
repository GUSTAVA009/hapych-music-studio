"""QA54 matched setting tests, no changes to live Music Studio.
Only CFG guidance changes; all else remains exactly QA52.
"""
from pathlib import Path
import py_compile,json
R=Path.home()/"Music Studio"
V=R/"Voice Engine";D=R/"Diagnostics"/"QA54";D.mkdir(exist_ok=True,parents=True)
parent=(V/"convert_track_studio52.py").read_text(encoding="utf-8")
needle="'--acoustic-prompt-seconds','18.0'"
assert parent.count(needle)==1
for rate in ("0.40","0.90"):
 s=parent.replace(needle,needle+",'--inference-cfg-rate','"+rate+"'")
 path=V/("convert_track_studio54_cfg"+rate.replace(".","")+".py")
 path.write_text(s,encoding="utf-8")
 py_compile.compile(str(path),doraise=True)
 print("QA54_FORK_COMPILED",path,flush=True)
data={"target_words":["дороги","горит"],"validation_words":["дождь","найдёшь","дышится","любить"],
 "experiment":"CFG 0.4 vs 0.9 against unchanged QA52 at 0.7",
 "seed":74191,"acoustic_prompt_seconds":18,"style_seconds":22,"voice":"alex_clean_qa44_v2",
 "steps":40,"other_parameters_unchanged":True,"production_settings_modified":False}
(D/"qa54_design.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

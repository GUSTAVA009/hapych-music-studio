"""QA52: controlled A/B vs QA51, change only matched acoustic prompt 15->18s.
No effect on active Music Studio, QA51, or voice model weights.
"""
from pathlib import Path
import py_compile,json
R=Path.home()/"Music Studio"; V=R/"Voice Engine"; D=R/"Diagnostics"/"QA52"
D.mkdir(exist_ok=True,parents=True)
inf=(V/"seed-vc"/"inference_studio51.py").read_text(encoding="utf-8")
src=V/"convert_track_studio51.py"; c=src.read_text(encoding="utf-8")
assert c.count("'--acoustic-prompt-seconds','15.0'")==1
assert c.count("inference_studio51.py")==1
assert 'qa51_reference_context' in inf
c=c.replace("'--acoustic-prompt-seconds','15.0'","'--acoustic-prompt-seconds','18.0'")
p=V/"convert_track_studio52.py"
p.write_text(c,encoding="utf-8");py_compile.compile(str(p),doraise=True)
q={"purpose":"18 second aligned acoustic conditioning vs QA51 15s","style_seconds":22,
   "controls":"same seed, source, microphone, model, 40 steps, F0 and mixing",
   "original_code_untouched":True,"trained_model_untouched":True}
(D/"qa52_trial_settings.json").write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA52_18S_CONTROLLED_FORK_READY")

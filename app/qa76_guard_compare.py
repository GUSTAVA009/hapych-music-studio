"""QA76 voice-drop guard comparison, same 35s source.
Does not certify perceptual quality. No production changes.
"""
from pathlib import Path
import sys,json
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA76";S=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
sys.path.insert(0,str(R/"Voice Engine"))
from voice_guard42 import check
paths={
"QA54":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav",
"QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
"APEX_FCPE":R/"Diagnostics"/"QA75"/"Apex_K4_Protect40_44k_dry.wav",
"APEX_RMVPE_P55":D/"RMVPE_K4_P55_44k_dry.wav",
"APEX_RMVPE_P80":D/"RMVPE_K4_P80_44k_dry.wav",
}
report={}
for k,p in paths.items():
 assert p.is_file(),p
 r=check(S,p,D/("guard_"+k+".json"),"ru")
 report[k]={"accepted":r["accepted"],"status":r["status"],"metrics":r["metrics"]}
 print("QA76_GUARD",k,json.dumps(report[k],ensure_ascii=True),flush=True)
(D/"qa76_guard_comparison.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

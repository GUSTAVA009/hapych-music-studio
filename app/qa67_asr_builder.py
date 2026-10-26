from pathlib import Path
import py_compile
root=Path.home()/"Music Studio";src=(root/"app"/"qa59_asr.py").read_text(encoding="utf-8")
a='''runs=json.loads((D/"qa59_inference_results.json").read_text(encoding="utf-8"))
paths={"source_ACE":Q/"QA54_CFG090_35s.source.wav","prior_QA54":Q/"QA54_CFG090_35s.dry.wav"}
for q in runs:
 if q.get("exit_code")==0 and q.get("audio"):
  paths["new_"+q["tag"]]=Path(q["audio"])
assert len(paths)>=3,paths'''
b='''paths={
 "source_ACE":Q/"QA54_CFG090_35s.source.wav",
 "prior_QA54":Q/"QA54_CFG090_35s.dry.wav",
 "QA66_prompt8":R/"Diagnostics"/"QA66"/"prompt_8sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA66_prompt12":R/"Diagnostics"/"QA66"/"prompt_12sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA67_timbre60":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s60_Dry.wav",
 "QA67_timbre95":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav"}
assert all(p.is_file() for p in paths.values())'''
assert src.count(a)==1
src=src.replace(a,b).replace('D=R/"Diagnostics"/"QA59"','D=R/"Diagnostics"/"QA67"')
src=src.replace('qa59_asr_compare.json','qa67_all_asr_comparison.json')
src=src.replace('QA59_ASR','QA67_ASR').replace('QA59_SCORES','QA67_SCORES')
dst=root/"app"/"qa67_all_asr.py"
dst.write_text(src,encoding="utf-8")
py_compile.compile(str(dst),doraise=True)
print("QA67_ASR_SETUP_OK",len(paths) if "paths" in globals() else dst)

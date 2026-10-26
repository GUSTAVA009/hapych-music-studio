from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
src=(R/"app"/"qa67_all_asr.py").read_text(encoding="utf-8")
a=''' "QA66_prompt8":R/"Diagnostics"/"QA66"/"prompt_8sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA66_prompt12":R/"Diagnostics"/"QA66"/"prompt_12sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA67_timbre60":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s60_Dry.wav",
 "QA67_timbre95":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav"}'''
b=''' "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
 "QA70_mic80_dyn30":D/"QA70_Mic80_Dyn30_Dry.wav",
 "QA70_mic80_dyn80":D/"QA70_Mic80_Dyn80_Dry.wav",
 "QA70_mic120_dyn55":D/"QA70_Mic120_Dyn55_Dry.wav",
 "QA70_mic60_dyn125":D/"QA70_Mic60_Dyn125_Dry.wav"}'''
assert src.count(a)==1
src=src.replace(a,b).replace('D=R/"Diagnostics"/"QA67"','D=R/"Diagnostics"/"QA70"')
src=src.replace('qa67_all_asr_comparison.json','qa70_asr_comparison.json')
src=src.replace('QA67_ASR','QA70_ASR').replace('QA67_SCORES','QA70_SCORES')
p=R/"app"/"qa70_asr.py"
p.write_text(src,encoding="utf-8");py_compile.compile(str(p),doraise=True)
print("QA70_ASR_READY")

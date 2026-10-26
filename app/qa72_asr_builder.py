from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
src=(R/"app"/"qa67_all_asr.py").read_text(encoding="utf-8")
a=''' "QA66_prompt8":R/"Diagnostics"/"QA66"/"prompt_8sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA66_prompt12":R/"Diagnostics"/"QA66"/"prompt_12sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA67_timbre60":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s60_Dry.wav",
 "QA67_timbre95":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav"}'''
b=''' "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
 "QA72_donor50":R/"Diagnostics"/"QA72"/"QA72_Donor50_Mic30_Dry.wav",
 "QA72_donor90":R/"Diagnostics"/"QA72"/"QA72_Donor90_Mic35_Dry.wav",
 "QA72_donor120":R/"Diagnostics"/"QA72"/"QA72_Donor120_Mic35_Dry.wav"}'''
assert src.count(a)==1
src=src.replace(a,b)
src=src.replace('D=R/"Diagnostics"/"QA67"','D=R/"Diagnostics"/"QA72"').replace('qa67_all_asr_comparison.json','qa72_asr_comparison.json').replace('QA67_ASR','QA72_ASR').replace('QA67_SCORES','QA72_SCORES')
out=R/"app"/"qa72_asr.py";out.write_text(src,encoding="utf-8");py_compile.compile(str(out),doraise=True)
print("QA72_ASR_SCRIPT_READY")

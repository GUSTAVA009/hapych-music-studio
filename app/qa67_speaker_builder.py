from pathlib import Path
import py_compile
root=Path.home()/"Music Studio";src=(root/"app"/"qa62_speaker_cos.py").read_text(encoding="utf-8")
old=''' "OpenVoice_t01":D/"QA62_OpenVoice_t01_raw.wav",
 "OpenVoice_t03":D/"QA62_OpenVoice_t03_raw.wav"}'''
new=''' "QA66_prompt8":R/"Diagnostics"/"QA66"/"prompt_8sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA66_prompt12":R/"Diagnostics"/"QA66"/"prompt_12sec"/"vc_QA54_CFG090_35s_reference_selected_1.0_40_0.9.wav",
 "QA67_timbre60":D/"QA67_ContinuousPhonemes_s60_Dry.wav",
 "QA67_timbre95":D/"QA67_ContinuousPhonemes_s95_Dry.wav"}'''
assert old in src
src=src.replace(old,new).replace('D=R/"Diagnostics"/"QA62"','D=R/"Diagnostics"/"QA67"').replace('qa62_speaker_comparison.json','qa67_speaker_comparison.json').replace('QA62_SPEAKER_COMPARE','QA67_SPEAKER_COMPARE')
dst=root/"app"/"qa67_speaker_cos.py";dst.write_text(src,encoding="utf-8");py_compile.compile(str(dst),doraise=True)
print("QA67_COS_SETUP_OK")

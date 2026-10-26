from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
src=(R/"app"/"qa69_pitch_audit.py").read_text(encoding="utf-8")
a='''paths={"ACE_original":q/"QA54_CFG090_35s.source.wav",
       "QA54_voice":q/"QA54_CFG090_35s.dry.wav",
       "QA66_prompt8":next((ref/"prompt_8sec").glob("vc_*.wav")),
       "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav"}'''
b='''paths={"ACE_original":q/"QA54_CFG090_35s.source.wav",
       "QA54_voice":q/"QA54_CFG090_35s.dry.wav",
       "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
       "QA73_vowel80":D/"QA73_Vowel_Mic80_Dyn80_Dry.wav",
       "QA73_vowel120":D/"QA73_Vowel_Mic120_Dyn55_Dry.wav",
       "QA73_vowel100":D/"QA73_Vowel_Mic100_Dyn15_Dry.wav"}'''
assert src.count(a)==1
src=src.replace(a,b).replace('D=R/"Diagnostics"/"QA69"','D=R/"Diagnostics"/"QA73"')
src=src.replace('qa69_pitch_report.json','qa73_pitch_report.json').replace('QA69_F0_DONE','QA73_F0_DONE').replace('QA69_PITCH','QA73_PITCH')
out=R/"app"/"qa73_pitch_audit.py";out.write_text(src,encoding="utf-8");py_compile.compile(str(out),doraise=True)
print("QA73_PITCH_SCRIPT_READY")

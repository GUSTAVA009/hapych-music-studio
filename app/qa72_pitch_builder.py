from pathlib import Path
import py_compile
R=Path.home()/"Music Studio";src=(R/"app"/"qa69_pitch_audit.py").read_text(encoding="utf-8")
a='''paths={"ACE_original":q/"QA54_CFG090_35s.source.wav",
       "QA54_voice":q/"QA54_CFG090_35s.dry.wav",
       "QA66_prompt8":next((ref/"prompt_8sec").glob("vc_*.wav")),
       "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav"}'''
b='''paths={"ACE_original":q/"QA54_CFG090_35s.source.wav",
       "QA54_voice":q/"QA54_CFG090_35s.dry.wav",
       "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
       "QA72_donor50":D/"QA72_Donor50_Mic30_Dry.wav",
       "QA72_donor90":D/"QA72_Donor90_Mic35_Dry.wav",
       "QA72_donor120":D/"QA72_Donor120_Mic35_Dry.wav"}'''
assert src.count(a)==1
src=src.replace(a,b).replace('D=R/"Diagnostics"/"QA69"','D=R/"Diagnostics"/"QA72"').replace('qa69_pitch_report.json','qa72_pitch_report.json').replace('QA69_F0_DONE','QA72_F0_DONE').replace('QA69_PITCH','QA72_PITCH')
out=R/"app"/"qa72_pitch_audit.py";out.write_text(src,encoding="utf-8");py_compile.compile(str(out),doraise=True)
print("QA72_PITCH_READY")

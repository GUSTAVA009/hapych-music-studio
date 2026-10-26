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
       "QA70_mic80_dyn30":D/"QA70_Mic80_Dyn30_Dry.wav",
       "QA70_mic80_dyn80":D/"QA70_Mic80_Dyn80_Dry.wav",
       "QA70_mic120_dyn55":D/"QA70_Mic120_Dyn55_Dry.wav",
       "QA70_mic60_dyn125":D/"QA70_Mic60_Dyn125_Dry.wav"}'''
assert src.count(a)==1
src=src.replace(a,b).replace('D=R/"Diagnostics"/"QA69"','D=R/"Diagnostics"/"QA70"')
src=src.replace('qa69_pitch_report.json','qa70_pitch_report.json').replace('QA69_F0_DONE','QA70_F0_DONE').replace('QA69_PITCH','QA70_PITCH')
out=R/"app"/"qa70_pitch_audit.py";out.write_text(src,encoding="utf-8");py_compile.compile(str(out),doraise=True)
print("QA70_PITCH_READY")

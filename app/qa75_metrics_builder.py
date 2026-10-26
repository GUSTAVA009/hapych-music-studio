from pathlib import Path
import py_compile
R=Path.home()/"Music Studio";A=R/"app"
s=(A/"qa72_speaker_metrics.py").read_text(encoding="utf-8")
a='''for c in json.loads((D/"qa72_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])
paths["QA70_best_prior"]=R/"Diagnostics"/"QA70"/"QA70_Mic60_Dyn125_Dry.wav"'''
b='''for c in json.loads((D/"qa75_benchmark.json").read_text(encoding="utf-8")):
 paths[c["version"]]=Path(c["dry_44k"])'''
assert s.count(a)==1
s=s.replace(a,b).replace('D=R/"Diagnostics"/"QA72"','D=R/"Diagnostics"/"QA75"')
s=s.replace('qa72_speaker_metrics.json','qa75_speaker_metrics.json').replace('QA72_OWNER_VOICE_COSINE','QA75_OWNER_VOICE_COSINE')
x=A/"qa75_speaker_metrics.py";x.write_text(s,encoding="utf-8");py_compile.compile(str(x),doraise=True)
s=(A/"qa72_asr.py").read_text(encoding="utf-8")
a=''' "QA72_donor50":R/"Diagnostics"/"QA72"/"QA72_Donor50_Mic30_Dry.wav",
 "QA72_donor90":R/"Diagnostics"/"QA72"/"QA72_Donor90_Mic35_Dry.wav",
 "QA72_donor120":R/"Diagnostics"/"QA72"/"QA72_Donor120_Mic35_Dry.wav"}'''
b=''' "Apex_K4_Protect40":D/"Apex_K4_Protect40_44k_dry.wav",
 "Apex_K8_Protect55":D/"Apex_K8_Protect55_44k_dry.wav"}'''
assert s.count(a)==1
s=s.replace(a,b).replace('D=R/"Diagnostics"/"QA72"','D=R/"Diagnostics"/"QA75"')
s=s.replace('qa72_asr_comparison.json','qa75_asr_comparison.json').replace('QA72_ASR','QA75_ASR').replace('QA72_SCORES','QA75_SCORES')
x=A/"qa75_asr.py";x.write_text(s,encoding="utf-8");py_compile.compile(str(x),doraise=True)
s=(A/"qa72_pitch_audit.py").read_text(encoding="utf-8")
a='''       "QA72_donor50":D/"QA72_Donor50_Mic30_Dry.wav",
       "QA72_donor90":D/"QA72_Donor90_Mic35_Dry.wav",
       "QA72_donor120":D/"QA72_Donor120_Mic35_Dry.wav"}'''
b='''       "Apex_K4_Protect40":D/"Apex_K4_Protect40_44k_dry.wav",
       "Apex_K8_Protect55":D/"Apex_K8_Protect55_44k_dry.wav"}'''
assert s.count(a)==1
s=s.replace(a,b).replace('D=R/"Diagnostics"/"QA72"','D=R/"Diagnostics"/"QA75"')
s=s.replace('qa72_pitch_report.json','qa75_pitch_report.json').replace('QA72_F0_DONE','QA75_F0_DONE').replace('QA72_PITCH','QA75_PITCH')
x=A/"qa75_pitch_audit.py";x.write_text(s,encoding="utf-8");py_compile.compile(str(x),doraise=True)
print("QA75_ALL_EVAL_SCRIPTS_READY")

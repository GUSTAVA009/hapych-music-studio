from pathlib import Path
import py_compile
R=Path.home()/"Music Studio";A=R/"app"
s=(A/"qa75_speaker_metrics.py").read_text(encoding="utf-8")
a='''for c in json.loads((D/"qa75_benchmark.json").read_text(encoding="utf-8")):
 paths[c["version"]]=Path(c["dry_44k"])'''
b='''for c in json.loads((D/"qa76_benchmark.json").read_text(encoding="utf-8")):
 paths[c["name"]]=Path(c["raw"])
paths["Apex_FCPE_K4"]=R/"Diagnostics"/"QA75"/"Apex_K4_Protect40_44k_dry.wav"'''
assert s.count(a)==1
s=s.replace(a,b).replace('D=R/"Diagnostics"/"QA75"','D=R/"Diagnostics"/"QA76"')
s=s.replace('qa75_speaker_metrics.json','qa76_speaker_metrics.json').replace('QA75_OWNER_VOICE_COSINE','QA76_OWNER_VOICE_COSINE')
p=A/"qa76_speaker_metrics.py";p.write_text(s,encoding="utf-8");py_compile.compile(str(p),doraise=True)
s=(A/"qa75_asr.py").read_text(encoding="utf-8")
a=''' "Apex_K4_Protect40":D/"Apex_K4_Protect40_44k_dry.wav",
 "Apex_K8_Protect55":D/"Apex_K8_Protect55_44k_dry.wav"}'''
b=''' "Apex_FCPE_K4":R/"Diagnostics"/"QA75"/"Apex_K4_Protect40_44k_dry.wav",
 "Apex_RMVPE_P55":D/"RMVPE_K4_P55_44k_dry.wav",
 "Apex_RMVPE_P80":D/"RMVPE_K4_P80_44k_dry.wav"}'''
assert s.count(a)==1
s=s.replace(a,b).replace('D=R/"Diagnostics"/"QA75"','D=R/"Diagnostics"/"QA76"')
s=s.replace('qa75_asr_comparison.json','qa76_asr_comparison.json').replace('QA75_ASR','QA76_ASR').replace('QA75_SCORES','QA76_SCORES')
p=A/"qa76_asr.py";p.write_text(s,encoding="utf-8");py_compile.compile(str(p),doraise=True)
s=(A/"qa75_pitch_audit.py").read_text(encoding="utf-8")
a='''       "Apex_K4_Protect40":D/"Apex_K4_Protect40_44k_dry.wav",
       "Apex_K8_Protect55":D/"Apex_K8_Protect55_44k_dry.wav"}'''
b='''       "Apex_FCPE_K4":R/"Diagnostics"/"QA75"/"Apex_K4_Protect40_44k_dry.wav",
       "Apex_RMVPE_P55":D/"RMVPE_K4_P55_44k_dry.wav",
       "Apex_RMVPE_P80":D/"RMVPE_K4_P80_44k_dry.wav"}'''
assert s.count(a)==1
s=s.replace(a,b).replace('D=R/"Diagnostics"/"QA75"','D=R/"Diagnostics"/"QA76"')
s=s.replace('qa75_pitch_report.json','qa76_pitch_report.json').replace('QA75_F0_DONE','QA76_F0_DONE').replace('QA75_PITCH','QA76_PITCH')
p=A/"qa76_pitch_audit.py";p.write_text(s,encoding="utf-8");py_compile.compile(str(p),doraise=True)
print("QA76_ALL_EVALUATORS_READY",flush=True)

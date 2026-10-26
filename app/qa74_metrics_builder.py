from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
base=(R/"app"/"qa70_speaker_metrics.py").read_text(encoding="utf-8")
a='''for c in json.loads((D/"qa70_timbre_transfer_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])'''
b='''for c in json.loads((D/"qa74_report.json").read_text(encoding="utf-8"))["candidate_results"]:
 paths[c["name"]]=Path(c["dry"])
paths["QA72_strong"] = R/"Diagnostics"/"QA72"/"QA72_Donor120_Mic35_Dry.wav"'''
assert base.count(a)==1
base=base.replace(a,b).replace('D=R/"Diagnostics"/"QA70"','D=R/"Diagnostics"/"QA74"').replace('qa70_speaker_metrics.json','qa74_speaker_metrics.json').replace('QA70_OWNER_VOICE_COSINE','QA74_OWNER_VOICE_COSINE')
name=R/"app"/"qa74_speaker_metrics.py";name.write_text(base,encoding="utf-8");py_compile.compile(str(name),doraise=True)
text=(R/"app"/"qa72_asr.py").read_text(encoding="utf-8")
a=''' "QA72_donor50":R/"Diagnostics"/"QA72"/"QA72_Donor50_Mic30_Dry.wav",
 "QA72_donor90":R/"Diagnostics"/"QA72"/"QA72_Donor90_Mic35_Dry.wav",
 "QA72_donor120":R/"Diagnostics"/"QA72"/"QA72_Donor120_Mic35_Dry.wav"}'''
b=''' "QA74_mag35":D/"QA74_FullMag_35_Dry.wav",
 "QA74_mag65":D/"QA74_FullMag_65_Dry.wav",
 "QA74_mag90":D/"QA74_FullMag_90_Dry.wav"}'''
assert text.count(a)==1
text=text.replace(a,b).replace('D=R/"Diagnostics"/"QA72"','D=R/"Diagnostics"/"QA74"').replace('qa72_asr_comparison.json','qa74_asr_comparison.json').replace('QA72_ASR','QA74_ASR').replace('QA72_SCORES','QA74_SCORES')
name=R/"app"/"qa74_asr.py";name.write_text(text,encoding="utf-8");py_compile.compile(str(name),doraise=True)
print("QA74_METRICS_SCRIPTS_READY")

from pathlib import Path
import json,py_compile
R=Path.home()/"Music Studio"
source=(R/"app"/"qa70_speaker_metrics.py").read_text(encoding="utf-8")
old='''for c in json.loads((D/"qa70_timbre_transfer_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])'''
new='''for c in json.loads((D/"qa72_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])
paths["QA70_best_prior"]=R/"Diagnostics"/"QA70"/"QA70_Mic60_Dyn125_Dry.wav"'''
assert source.count(old)==1
source=source.replace(old,new).replace('D=R/"Diagnostics"/"QA70"','D=R/"Diagnostics"/"QA72"')
source=source.replace('qa70_speaker_metrics.json','qa72_speaker_metrics.json')
source=source.replace('QA70_OWNER_VOICE_COSINE','QA72_OWNER_VOICE_COSINE')
dst=R/"app"/"qa72_speaker_metrics.py"
dst.write_text(source,encoding="utf-8");py_compile.compile(str(dst),doraise=True)
print("QA72_METRIC_SCRIPT_COMPILED")

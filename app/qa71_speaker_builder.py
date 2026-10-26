from pathlib import Path
import json,py_compile
R=Path.home()/"Music Studio"
source=(R/"app"/"qa70_speaker_metrics.py").read_text(encoding="utf-8")
old='''for c in json.loads((D/"qa70_timbre_transfer_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])'''
new='''for c in json.loads((D/"qa71_report.json").read_text(encoding="utf-8"))["variant_results"]:
 paths[c["name"]]=Path(c["dry"])
paths["QA70_best_current"]=R/"Diagnostics"/"QA70"/"QA70_Mic60_Dyn125_Dry.wav"'''
assert source.count(old)==1
source=source.replace(old,new)
source=source.replace('D=R/"Diagnostics"/"QA70"','D=R/"Diagnostics"/"QA71"')
source=source.replace('qa70_speaker_metrics.json','qa71_speaker_metrics.json')
source=source.replace('QA70_OWNER_VOICE_COSINE','QA71_OWNER_VOICE_COSINE')
dest=R/"app"/"qa71_speaker_metrics.py"
dest.write_text(source,encoding="utf-8")
py_compile.compile(str(dest),doraise=True)
print("QA71_SPEAKER_BENCH_SETUP_OK")

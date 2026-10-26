from pathlib import Path
import py_compile
R=Path.home()/"Music Studio";src=(R/"app"/"qa70_speaker_metrics.py").read_text(encoding="utf-8")
old='''for c in json.loads((D/"qa70_timbre_transfer_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])'''
new='''for c in json.loads((D/"qa73_timbre_transfer_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])
paths["QA70_prior_mic120"]=R/"Diagnostics"/"QA70"/"QA70_Mic120_Dyn55_Dry.wav"'''
assert src.count(old)==1
src=src.replace(old,new).replace('D=R/"Diagnostics"/"QA70"','D=R/"Diagnostics"/"QA73"')
src=src.replace('qa70_speaker_metrics.json','qa73_speaker_metrics.json').replace('QA70_OWNER_VOICE_COSINE','QA73_OWNER_VOICE_COSINE')
out=R/"app"/"qa73_speaker_metrics.py"
out.write_text(src,encoding="utf-8");py_compile.compile(str(out),doraise=True)
print("QA73_SPEAKER_METRIC_SCRIPT_READY")

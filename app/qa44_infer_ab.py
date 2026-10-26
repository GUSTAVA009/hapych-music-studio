"""QA44 isolated personal-model validation launcher.
Use identical QA43 source, same 22s known mic reference, same steps and seed.
Never deploy results to app/library. Holds out one independent microphone sample.
"""
from pathlib import Path
import json,subprocess,sys,time
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA44";D.mkdir(exist_ok=True,parents=True)
src=R/"Voice Engine"/"convert_track_studio40.py"
dst=R/"Voice Engine"/"convert_track_studio44.py"
s=src.read_text(encoding="utf-8")
old="folder=VOICE/'runs'/'music_studio_personal_v1'"
new="folder=VOICE/'runs'/'alex_clean_qa44_v2'"
assert s.count(old)==1
dst.write_text(s.replace(old,new),encoding="utf-8")
__import__("py_compile").compile(str(dst),doraise=True)
run=R/"Voice Engine"/"seed-vc"/"runs"/"alex_clean_qa44_v2"
chk=run/"ft_model.pth";cfg=run/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"
if not chk.is_file() or chk.stat().st_size<100_000_000 or not cfg.is_file():
 raise RuntimeError("Trained v2 checkpoint not ready")
data=json.loads((D/"qa44_v2_manifest.json").read_text(encoding="utf-8"))
assert data["run_name"]=="alex_clean_qa44_v2" and len([s for s in data["samples"] if s["role"]=="train"])==3
source=R/"Diagnostics"/"QA43"/"QA43_QA42_SUNG_SOURCE_35to75.wav"
reference=next((R/"Мой голос").glob("*3867cb.wav"))
out=D/"QA44_Finetuned_40s_MyVoice_22sec.mp3"
py=R/"Voice Engine"/".venv"/"Scripts"/"python.exe"
command=[str(py),"-u",str(dst),"--source",str(source),"--voice",str(reference),
 "--output",str(out),"--steps","40","--trained","--register","original",
 "--language","ru","--keep-dry"]
start=time.monotonic()
p=subprocess.run(command,capture_output=True,text=True,timeout=1200)
(D/"qa44_voice_run_out.log").write_text(p.stdout,encoding="utf-8")
(D/"qa44_voice_run_err.log").write_text(p.stderr,encoding="utf-8")
report={"exit_code":p.returncode,"elapsed_seconds":round(time.monotonic()-start,1),
 "new_model":"alex_clean_qa44_v2","source_qa42_file":str(source),
 "reference":reference.name,"same_settings_as_QA43":True,"deployed":False,
 "output":str(out),"file_exists":out.is_file(),"error_excerpt":p.stderr[-1400:]}
if out.is_file():
 q=out.with_suffix(".quality.json")
 if q.exists():
  metrics=json.loads(q.read_text(encoding="utf-8"))
  report.update({"speaker_embedding_cosine":metrics.get("speaker_embedding_cosine"),
                 "f0_status":metrics.get("pitch_consistency",{}).get("status"),
                 "continuity":metrics.get("voice_check",{}).get("metrics"),
                 "voice_check_accepted":metrics.get("voice_check",{}).get("accepted")})
(D/"qa44_inference_result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_PERSONAL_INFER",json.dumps({k:v for k,v in report.items() if k!="error_excerpt"},ensure_ascii=True),flush=True)
if p.returncode!=0:
 print("INFERENCE_ERROR",report["error_excerpt"][-1200:],flush=True);sys.exit(p.returncode)

"""HAPYCH offline Russian Orthoepy CLI.
Example:
  .venv-transcript/Scripts/python.exe analyze_lyrics.py --source lyrics.json --out-dir QA123
Input JSON requires a lyrics string. No cloud, no voice recording access,
and no modifications to ACE-Step, Studio UI or original source.
"""
from pathlib import Path
import argparse,os,json,subprocess,sys,hashlib,time
ROOT=Path(__file__).resolve().parent
def run(source:Path,output_dir:Path)->dict:
 source=source.resolve()
 assert source.is_file() and source.suffix.lower()==".json"
 text=json.loads(source.read_text(encoding="utf8"))
 assert isinstance(text,dict) and isinstance(text.get("lyrics"),str)
 assert text["lyrics"].strip() and len(text["lyrics"])<6000
 output_dir=output_dir.resolve();output_dir.mkdir(parents=True,exist_ok=True)
 stress=output_dir/"orthoepy_stress.json"
 ipa=output_dir/"orthoepy_ipa.json"
 review=output_dir/"orthoepy_review.txt"
 exe1=ROOT/".venv"/"Scripts"/"python.exe"
 exe2=ROOT/".venv-transcript"/"Scripts"/"python.exe"
 for p in (exe1,exe2):assert p.is_file(),p
 env=os.environ.copy()
 env.update(PYTHONUTF8="1",HF_HUB_OFFLINE="1",
  TRANSFORMERS_OFFLINE="1",
  HAPYCH_SOURCE_JSON=str(source),
  HAPYCH_STRESS_JSON=str(stress),
  HAPYCH_IPA_JSON=str(ipa),
  HAPYCH_IPA_REVIEW=str(review))
 start=time.monotonic()
 for exe,script in [
   (exe1,ROOT/"qa121_stress.py"),
   (exe2,ROOT/"qa121_phonemes.py")]:
  process=subprocess.run([str(exe),"-X","utf8","-u",str(script)],
   env=env,capture_output=True,text=True,timeout=90)
  if process.returncode:
   raise RuntimeError(f"{script.name} failed: {process.stderr[-1500:]} "
      f"{process.stdout[-800:]}")
  print(f"{script.name}: finished; final line = "
   + (process.stdout.strip().splitlines()[-1] if process.stdout else "<no output>"),
   flush=True)
 obj=json.loads(ipa.read_text(encoding="utf8"))
 assert len(obj["qa"])>=1
 assert obj["current_ACE_does_NOT_consume_IPA"]
 assert obj["exact_note_alignment_supported"] is False
 summary={"source":str(source),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
  "lines":len(obj["qa"]),
  "stressed_word_examples":[x["reviewed_stress"] for x in obj["qa"][:5]],
  "stress_json":str(stress),"ipa_json":str(ipa),"review_txt":str(review),
  "elapsed_seconds":round(time.monotonic()-start,2),
  "audio_generated":False,"cloud_spending":0,
  "existing_songs_and_models_modified":False,
  "next_stage":"phoneme-to-musical-note durations, requires trained singing synth"}
 (output_dir/"run_summary.json").write_text(
  json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf8")
 return summary
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--source",type=Path,required=True)
 p.add_argument("--out-dir",type=Path,required=True)
 a=p.parse_args()
 print("ORTHOEPY_PIPELINE_DONE",
  json.dumps(run(a.source,a.out_dir),ensure_ascii=False),flush=True)

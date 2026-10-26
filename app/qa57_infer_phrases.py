"""QA57 deterministic short-phrase inference (one mel chunk per phrase).
Target: avoid 35s mid-word cut and internal mel overlap while retaining
original QA44 personal model and 18s prompt, CFG 0.90, 40 steps.
"""
from pathlib import Path
import os,sys,json,subprocess,time
import numpy as np,soundfile as sf
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA57";V=R/"Voice Engine";SEED=V/"seed-vc"
data=json.loads((D/"qa57_inputs.json").read_text(encoding="utf-8"))
p=SEED/"runs"/"alex_clean_qa44_v2"
checkpoint=p/"ft_model.pth";config=p/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"
assert checkpoint.is_file() and config.is_file()
assert len(data["phrase_clips"])==5
ref=data["ref_selected"];assert Path(ref).is_file()
exe=V/".venv"/"Scripts"/"python.exe"
out=[]
for seg in data["phrase_clips"]:
 idx=seg["id"]
 src=Path(seg["filename"]);destination=D/("synth_phrase%02d"%idx);destination.mkdir(exist_ok=True)
 stored=sorted(destination.glob("vc_*.wav"))
 if stored:
  output=stored[0]
  print("QA57_RESUME",idx,str(output),flush=True)
 else:
  command=[str(exe),"-u","inference_studio51.py","--source",str(src),
     "--target",str(ref),"--output",str(destination),
     "--checkpoint",str(checkpoint),"--config",str(config),
     "--diffusion-steps","40","--f0-condition","True","--fp16","True",
     "--auto-f0-adjust","False","--semi-tone-shift","0",
     "--register","original","--seed","74191",
     "--acoustic-prompt-seconds","18.0","--inference-cfg-rate","0.90"]
  env=os.environ.copy();env.update(HF_HUB_DISABLE_TELEMETRY="1",PYTHONUTF8="1")
  st=time.monotonic()
  with (D/("qa57_phrase%02d_stdout.log"%idx)).open("w",encoding="utf-8") as log:
   rc=subprocess.run(command,cwd=str(SEED),stdout=log,stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL,timeout=480,env=env).returncode
  if rc:raise RuntimeError("Phrase %d failed (%d), check log"%(idx,rc))
  stored=sorted(destination.glob("vc_*.wav"))
  assert len(stored)==1,stored
  output=stored[0]
  print("QA57_PHRASE_SYNTH_COMPLETE",idx,round(time.monotonic()-st,1),flush=True)
 audio,sr=sf.read(output,dtype="float32",always_2d=True)
 assert sr==44100 and audio.shape[1] in [1,2]
 expected=seg["duration_s"]
 actual=len(audio)/sr
 assert abs(actual-expected)<.30,(idx,actual,expected)
 q=json.loads((destination/"register_report.json").read_text(encoding="utf-8"))
 chunks=q.get("stitching",{}).get("diffusion_chunks")
 assert chunks==1,(idx,chunks,q.get("stitching"))
 out.append({"phrase_id":idx,"converted":str(output),"duration_s":round(actual,3),
   "source_duration_s":expected,"chunks":chunks,"speaker_cosine_proxy":q.get("speaker_embedding_cosine"),
   "pitch_status":q.get("pitch_consistency",{}).get("status")})
 (D/"qa57_phrase_progress.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA57_ONE_CHUNK_VERIFIED",json.dumps(out[-1],ensure_ascii=True),flush=True)
print("QA57_ALL_PHRASES_READY",len(out),flush=True)

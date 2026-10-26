"""QA60 controlled checkpoint ablation: untouched Seed-VC foundation vs QA54 personalized.
Uses SAME source stem, 22s microphone reference, 18s prompt,
40 diffusion steps, CFG .90, seed 74191 and register original.
Outputs *isolated diagnostic file* only. No live model or app changes.
"""
from pathlib import Path
import subprocess,time,sys,json,hashlib,requests
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA60";D.mkdir(parents=True,exist_ok=True)
Q=R/"Diagnostics"/"QA54";V=R/"Voice Engine";S=V/"seed-vc"
s=Q/"QA54_CFG090_35s.source.wav"
ref=R/"Diagnostics"/"QA57"/"reference_selected.wav"
assert s.is_file() and ref.is_file()
h=requests.Session();h.trust_env=False
health=h.get("http://127.0.0.1:7870/api/health",timeout=7).json()
assert health["job"]["status"] not in ("generating","converting","preparing")
report={"model":"unmodified official Seed-VC 44k F0 checkpoint",
        "control":"QA54 trained personal on exact same source/ref/settings",
        "source":str(s),"reference":str(ref),
        "source_sha256":hashlib.sha256(s.read_bytes()).hexdigest(),
        "reference_sha256":hashlib.sha256(ref.read_bytes()).hexdigest(),
        "inference":{"steps":40,"seed":74191,"cfg":0.9,
                     "f0_condition":True,"register":"original","acoustic_prompt_seconds":18},
        "no_production_changes":True,"no_new_training":True}
(D/"qa60_control_plan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
command=[str(V/".venv"/"Scripts"/"python.exe"),"-u","inference_studio51.py",
"--source",str(s),"--target",str(ref),"--output",str(D/"base_inference"),
"--diffusion-steps","40","--f0-condition","True","--fp16","True",
"--auto-f0-adjust","False","--semi-tone-shift","0",
"--register","original","--seed","74191",
"--acoustic-prompt-seconds","18.0","--inference-cfg-rate","0.9"]
print("START_QA60_BASE_CONTROL",flush=True)
start=time.monotonic()
with (D/"qa60_infer_log.txt").open("w",encoding="utf-8") as log:
 try:
  rc=subprocess.run(command,cwd=str(S),stdout=log,stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,timeout=480).returncode
 except subprocess.TimeoutExpired:
  rc=124
outputs=list((D/"base_inference").glob("vc_*.wav"))
state={"exit":rc,"elapsed":round(time.monotonic()-start,1),
       "audio_file":str(outputs[0]) if len(outputs)==1 else None}
if len(outputs)==1:
 state["file_bytes"]=outputs[0].stat().st_size
(D/"qa60_infer_result.json").write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA60_BASE_INFERENCE_RESULT",json.dumps(state,ensure_ascii=True),flush=True)
sys.exit(rc)

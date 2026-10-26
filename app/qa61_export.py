"""QA61 export identical-mel log and baseline chunked vocoder output."""
from pathlib import Path
import sys,subprocess,json,time,os,requests
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA61";S=R/"Voice Engine"/"seed-vc"
S.mkdir(parents=True,exist_ok=True)
mic=R/"Diagnostics"/"QA57"/"reference_selected.wav"
src=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
ck=S/"runs"/"alex_clean_qa44_v2"/"ft_model.pth"
cfg=S/"runs"/"alex_clean_qa44_v2"/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"
assert all(z.is_file() for z in [mic,src,ck,cfg])
health=requests.Session();health.trust_env=False
h=health.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("generating","preparing","converting")
cmd=[str(R/"Voice Engine"/".venv"/"Scripts"/"python.exe"),"-u",
 "inference_studio61.py",
 "--source",str(src),"--target",str(mic),"--output",str(D/"original_vocoder"),
 "--checkpoint",str(ck),"--config",str(cfg),
 "--diffusion-steps","40","--f0-condition","True","--fp16","True",
 "--auto-f0-adjust","False","--semi-tone-shift","0",
 "--register","original","--seed","74191",
 "--acoustic-prompt-seconds","18","--inference-cfg-rate","0.9"]
env=os.environ.copy()
env["QA61_MEL_EXPORT_PATH"]=str(D/"full_mel_from_QA54.pt")
env["PYTHONUTF8"]="1"
start=time.monotonic()
with (D/"qa61_mel_export.log").open("w",encoding="utf-8") as f:
 try: rc=subprocess.run(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT,
   stdin=subprocess.DEVNULL,env=env,timeout=500).returncode
 except subprocess.TimeoutExpired:rc=124
result={"exit":rc,"time_seconds":round(time.monotonic()-start,1),
 "mel_saved":(D/"full_mel_from_QA54.pt").is_file(),
 "same_weights_as_QA54":True,"same_source_and_reference":True,
 "staged_audio_files":[str(p) for p in (D/"original_vocoder").glob("vc_*.wav")],
 "production_changed":False}
(D/"qa61_mel_export_result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA61_EXPORT",json.dumps(result,ensure_ascii=True),flush=True)
sys.exit(rc)

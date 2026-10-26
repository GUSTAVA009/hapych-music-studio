"""QA59 train runner with SAFE isolated fork of known-low-VRAM trainer.
Seed-VC foundation architecture stays identical; no production overwrites.
Parameter changes: deterministic seeds, non-dropping Whisper inference, LR 6e-6,
270 steps, checkpoint retention. No extra voices, no fake augmentations.
"""
from pathlib import Path
import json,os,random,subprocess,sys,hashlib,time
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";V=R/"Voice Engine";S=V/"seed-vc"
manifest=json.loads((D/"qa59_dataset_manifest.json").read_text(encoding="utf-8"))
assert len(manifest["segments"])==10 and manifest["only_mic_with_user_consent"]
assert len(manifest["heldout_files"])==1
assert manifest["training_audio_real_seconds"]>74
assert all((D/"curated_44k"/e["file"]).exists() for e in manifest["segments"])
src=S/"train_hapych_lowvram.py";parent=src.read_text(encoding="utf-8")
fork=S/"train_qa59_curated.py";p=parent
assert p.count('"base_lr": 0.00001')==1
p=p.replace('"base_lr": 0.00001','"base_lr": 0.000006')
assert p.count("if len(checkpoints) > 2:")==1
p=p.replace("if len(checkpoints) > 2:","if len(checkpoints) > 10000:")
assert p.count("self.whisper_model = WhisperModel.from_pretrained(whisper_model_name).to(device)")==1
p=p.replace("self.whisper_model = WhisperModel.from_pretrained(whisper_model_name).to(device)",
"self.whisper_model = WhisperModel.from_pretrained(whisper_model_name).to(device).eval()")
assert p.count("    trainer = Trainer(")==1
p=p.replace("    trainer = Trainer(",'''    # Deterministic checkpoint comparison with unchanged data order.
    import numpy as np
    random.seed(5929)
    np.random.seed(5929)
    torch.manual_seed(5929)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(5929)
    trainer = Trainer(''')
fork.write_text(p,encoding="utf-8")
import py_compile
py_compile.compile(str(fork),doraise=True)
base=S/"checkpoints"/"models--Plachta--Seed-VC"/"snapshots"/"257283f9f41585055e8f858fba4fd044e5caed6e"/"DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth"
assert base.exists() and base.stat().st_size>700_000_000
out=S/"runs"/"alex_voice_qa59_curated_270"
assert not out.exists(),"QA59 unique run already exists; prevent overwrite"
# Make sure current app and model training have no active generation.
import requests
session=requests.Session();session.trust_env=False
h=session.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("generating","preparing","converting")
assert not any(h.get(k,{}).get("active") for k in ("training23","training32","training41"))
report={"train_script":str(fork),"source_script_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
        "training_mode":"full fine-tune from original approved Seed-VC base 44.1k F0",
        "training_clips":10,"real_training_seconds":manifest["training_audio_real_seconds"],
        "holdout":manifest["heldout_files"],"source_base":str(base),
        "batch_size":1,"max_steps":270,"max_epochs":40,"intermediate_save_steps":[90,180],
        "learning_rate":6e-6,"seed":5929,
        "train_only_clean_mic":True,"external_data":False,
        "production_deployment":False,"existing_models_unmodified":True}
(D/"qa59_train_plan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
cmd=[str(V/".venv"/"Scripts"/"python.exe"),"-u",str(fork),
 "--config","configs/presets/config_dit_mel_seed_uvit_whisper_base_f0_44k.yml",
 "--pretrained-ckpt",str(base),"--dataset-dir",str(D/"curated_44k"),
 "--run-name","alex_voice_qa59_curated_270",
 "--batch-size","1","--max-steps","270","--max-epochs","40",
 "--save-every","90","--num-workers","0"]
env=os.environ.copy();env.update(PYTHONIOENCODING="utf-8",PYTHONUTF8="1",
                                HF_HUB_DISABLE_TELEMETRY="1",
                                NO_PROXY="127.0.0.1,localhost,::1",
                                no_proxy="127.0.0.1,localhost,::1")
log=D/"qa59_training.log"
t=time.monotonic()
with log.open("w",encoding="utf-8") as f:
 try:
  p=subprocess.run(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                   timeout=1300,env=env)
  resultcode=p.returncode
 except subprocess.TimeoutExpired:
  resultcode=124
chks=sorted((S/"runs"/"alex_voice_qa59_curated_270").glob("*.pth"))
rr={"exit":resultcode,"elapsed_s":round(time.monotonic()-t,2),
 "checkpoint_names":[{"name":x.name,"size":x.stat().st_size} for x in chks],
 "log":str(log),"latest_model":str(out/"ft_model.pth"),
 "deployed":False,"train_samples":10}
(D/"qa59_train_result.json").write_text(json.dumps(rr,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA59_TRAIN_RESULT",json.dumps(rr,ensure_ascii=True),flush=True)
if resultcode!=0:sys.exit(resultcode)

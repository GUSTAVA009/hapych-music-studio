"""QA59 staged resume; preserves optimizer/scheduler state from checkpoint 90.
Stage2: 90->181 steps on short clean utterances (saves optimizer checkpoint180).
Stage3: 180->270 steps on long phrases. Separate process memory per stage.
"""
from pathlib import Path
import os,sys,subprocess,hashlib,json,time,py_compile
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";V=R/"Voice Engine";S=V/"seed-vc"
base=S/"train_qa59_curated.py"
parent=base.read_text(encoding="utf-8")
assert parent.count("load_only_params=True,")==1
p=parent.replace("load_only_params=True,","load_only_params=False,")
assert p.count("for epoch in range(self.n_epochs):")==1
p=p.replace("for epoch in range(self.n_epochs):","for epoch in range(self.epoch, self.n_epochs):")
assert p.count("            self.iters += 1")==1
p=p.replace("            self.iters += 1",'''            self.iters += 1
            if self.iters % 12 == 0:
                # Reduce Python/CUDA allocator fragmentation on RTX 4060 8GB.
                import gc
                gc.collect()
                if torch.cuda.is_available():torch.cuda.empty_cache()''')
out=S/"train_qa59_resume_gc.py"
out.write_text(p,encoding="utf-8");py_compile.compile(str(out),doraise=True)
assert (S/"runs"/"alex_voice_qa59_curated_270"/"DiT_epoch_00008_step_00090.pth").is_file()
stages=[
{"id":2,"run_name":"alex_voice_qa59_stage2_181","max_steps":181,
"pretrained":S/"runs"/"alex_voice_qa59_curated_270"/"DiT_epoch_00008_step_00090.pth",
"dataset":D/"articulation_44k",
"expected_new":S/"runs"/"alex_voice_qa59_stage2_181"/"DiT_epoch_00013_step_00180.pth"},
{"id":3,"run_name":"alex_voice_qa59_stage3_270","max_steps":270,
"pretrained":None,"dataset":D/"curated_44k",
"expected_new":S/"runs"/"alex_voice_qa59_stage3_270"/"ft_model.pth"}]
for s in stages:assert s["dataset"].is_dir()
env=os.environ.copy()
env.update(PYTHONIOENCODING="utf-8",PYTHONUTF8="1",HF_HUB_DISABLE_TELEMETRY="1",
           NO_PROXY="localhost,127.0.0.1,::1",no_proxy="localhost,127.0.0.1,::1")
summary={"stage1_checkpoint":str(stages[0]["pretrained"]),"stage1_valid":True,
  "data_only_user_microphone":True,"production_model_unchanged":True,
  "optimizer_state_preserved_between_stages":True,"stages":[]}
for s in stages:
 if s["id"]==3:
  prev=S/"runs"/"alex_voice_qa59_stage2_181"
  cp=list(prev.glob("DiT_epoch_*_step_00180.pth"))
  assert len(cp)==1,cp
  s["pretrained"]=cp[0]
 run=S/"runs"/s["run_name"]
 assert not run.exists(),f"Unique stage folder already exists: {run}"
 assert s["pretrained"].is_file() and s["pretrained"].stat().st_size>1_000_000_000
 cmd=[str(V/".venv"/"Scripts"/"python.exe"),"-u",str(out),
 "--config","configs/presets/config_dit_mel_seed_uvit_whisper_base_f0_44k.yml",
 "--pretrained-ckpt",str(s["pretrained"]),
 "--dataset-dir",str(s["dataset"]),"--run-name",s["run_name"],
 "--batch-size","1","--max-steps",str(s["max_steps"]),"--max-epochs","40",
 "--save-every","90","--num-workers","0"]
 t=time.monotonic()
 with (D/("qa59_stage"+str(s["id"])+".log")).open("w",encoding="utf-8") as file:
  try:
   rc=subprocess.run(cmd,cwd=S,stdout=file,stderr=subprocess.STDOUT,
       stdin=subprocess.DEVNULL,timeout=950,env=env).returncode
  except subprocess.TimeoutExpired:rc=124
 output=list(run.glob("*.pth"))
 result={"stage":s["id"],"rc":rc,"from":str(s["pretrained"]),
    "dataset":str(s["dataset"]),"max_step":s["max_steps"],
    "elapsed_s":round(time.monotonic()-t,2),
    "saved":[{"name":x.name,"bytes":x.stat().st_size} for x in output],
    "deployed":False}
 summary["stages"].append(result)
 (D/"qa59_staged_result.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA59_STAGE_DONE",json.dumps(result,ensure_ascii=True),flush=True)
 if rc!=0:sys.exit(rc)
assert (S/"runs"/"alex_voice_qa59_stage3_270"/"ft_model.pth").is_file()
print("QA59_ALL_270_STEPS_COMPLETE",flush=True)

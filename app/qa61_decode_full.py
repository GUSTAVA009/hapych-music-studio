"""QA61 BigVGAN continuous decode of EXACT log-mel from QA54-compatible Seed-VC.
Separate process: only vocoder on GPU, no Whisper/DiT competing for VRAM.
Diagnostic WAV and objective seam metrics; no live model changes.
"""
from pathlib import Path
import torch, numpy as np,soundfile as sf,time,json,sys
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA61";S=R/"Voice Engine"/"seed-vc"
import os
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache')
os.environ['HF_HUB_OFFLINE']='1'
os.chdir(S)
data=torch.load(D/"full_mel_from_QA54.pt",map_location="cpu",weights_only=True)
mel=data["mel"].float()
assert mel.ndim==3 and mel.shape[0]==1 and mel.shape[1]==128
sr=int(data["sample_rate"]);hop=int(data["hop_length"])
assert sr==44100 and hop==512
import yaml
cfg=yaml.safe_load((S/"runs"/"alex_clean_qa44_v2"/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml").read_text(encoding="utf-8"))
name=cfg["model_params"]["vocoder"]["name"]
assert name=="nvidia/bigvgan_v2_44khz_128band_512x"
sys.path.insert(0,str(S))
from modules.bigvgan import bigvgan
device="cuda" if torch.cuda.is_available() else "cpu"
if device=="cuda":torch.cuda.empty_cache()
model=bigvgan.BigVGAN.from_pretrained(name,use_cuda_kernel=False)
model.remove_weight_norm()
model=model.eval().to(device)
print("QA61_MEL",list(mel.shape),sr,hop,"vocoder",name,"device",device,flush=True)
t=time.monotonic()
status={"method":"one full uninterrupted BigVGAN pass of original 35s mel",
 "mel_size":list(mel.shape),"device":device,"successful":False,"production_untouched":True}
try:
 with torch.inference_mode():
  wave=model(mel.to(device)).reshape(-1).detach().float().cpu().numpy()
 if device=="cuda":status["peak_gpu_mem_gb"]=round(torch.cuda.max_memory_allocated()/2**30,2)
 status["successful"]=True
except RuntimeError as e:
 status["error"]=str(e)[:1000]
 print("QA61_SINGLE_PASS_FAILED",status["error"],flush=True)
 (D/"qa61_full_vocoder_report.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
 raise
assert wave.size==mel.shape[-1]*hop,(wave.size,mel.shape,hop)
assert np.all(np.isfinite(wave))
peak=float(np.max(np.abs(wave)))
assert peak<=1.1,peak
sf.write(D/"QA61_Continuous_BigVGAN_Dry.wav",wave,sr,subtype="FLOAT")
oldfile=list((D/"original_vocoder").glob("vc_*.wav"))
assert len(oldfile)==1
old,s_old=sf.read(oldfile[0],dtype="float32",always_2d=True)
assert s_old==sr and len(old)==len(wave)
old=old.mean(axis=1)
seam_frame=512
boundaries=[j*seam_frame*hop for j in range(1,10) if j*seam_frame*hop<len(wave)]
measures=[]
for ix in boundaries:
 left=max(0,ix-int(.07*sr));right=min(len(wave),ix+int(.07*sr))
 def evaluate(x):
  ds=np.abs(np.diff(x[left:right]))
  median=float(np.median(ds))
  jump=float(abs(x[ix]-x[ix-1]))
  r1=float(np.sqrt(np.mean(x[left:ix]**2)+1e-12))
  r2=float(np.sqrt(np.mean(x[ix:right]**2)+1e-12))
  return {"jump":round(jump,5),"relative_jump":round(jump/max(1e-6,median),2),
    "rms_step_db_70ms":round(abs(20*np.log10(max(r2,1e-8)/max(r1,1e-8))),2)}
 measures.append({"time":round(ix/sr,3),"old_chunks":evaluate(old),"continuous":evaluate(wave)})
status.update(successful=True,seconds=round(time.monotonic()-t,2),
              wav=str(D/"QA61_Continuous_BigVGAN_Dry.wav"),peak=round(peak,4),
              seam_measures=measures,
              waveform_difference_rms=round(float(np.sqrt(np.mean((old-wave)**2))),5),
              continuous_rms=round(float(np.sqrt(np.mean(wave**2))),5))
(D/"qa61_full_vocoder_report.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA61_FULL_VOCODER_SUCCESS",json.dumps(status,ensure_ascii=True),flush=True)

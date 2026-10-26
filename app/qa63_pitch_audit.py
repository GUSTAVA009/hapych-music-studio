"""QA63 F0 timeline audit of unmodified source / QA54 / failed QA62 tracks.
Output is numerical evidence only; a pitch-contour match does not prove natural phrasing.
"""
import os,sys,time,json
from pathlib import Path
import numpy as np,soundfile as sf,torch,torchaudio
R=Path.home()/"Music Studio";S=R/"Voice Engine"/"seed-vc";D=R/"Diagnostics"/"QA63"
D.mkdir(parents=True,exist_ok=True);os.chdir(S);sys.path.insert(0,str(S))
os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1"
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
ckpt=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
model=RMVPE(ckpt,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
paths={
 "source_ACE":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav",
 "QA54_personal":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav",
 "QA62_OpenVoice_01":R/"Diagnostics"/"QA62"/"QA62_OpenVoice_t01_raw.wav",
 "QA62_OpenVoice_03":R/"Diagnostics"/"QA62"/"QA62_OpenVoice_t03_raw.wav"}
f0={}
for name,path in paths.items():
 assert path.exists(),path
 audio,sr=sf.read(path,dtype="float32",always_2d=True)
 wav=torch.from_numpy(audio.mean(axis=1).copy()).float()
 if sr!=16000:wav=torchaudio.functional.resample(wav,sr,16000)
 begin=time.monotonic()
 seq=np.asarray(model.infer_from_audio(wav,thred=.03),dtype=float).reshape(-1)
 seq[~np.isfinite(seq)]=0
 f0[name]=seq
 print("QA63_F0_DONE",name,"frames",len(seq),"voiced_frac",round(float(np.mean(seq>55)),3),"s",round(time.monotonic()-begin,2),flush=True)
n=min(map(len,f0.values()))
ref=f0["source_ACE"][:n]
summary={}
for name,seq in f0.items():
 y=seq[:n];expected=(ref>55)&(ref<1200);actual=(y>55)&(y<1200)
 both=expected&actual
 delta=np.zeros(n);delta[both]=12*np.log2(y[both]/ref[both])
 detail=[]
 for begin in np.arange(0,min(35,int(n/100)),5,dtype=float):
  a=int(begin*100);b=min(n,a+500)
  active=expected[a:b]
  valid=both[a:b]
  local=np.abs(delta[a:b][valid])
  detail.append({
   "window_s":[int(begin),int(begin+5)],
   "source_voiced_frames":int(active.sum()),
   "candidate_voiced_frames":int(actual[a:b].sum()),
   "source_voiced_missing_fraction":round(float(np.mean(~actual[a:b][active])),3) if active.any() else None,
   "pitch_abs_median_semitones":round(float(np.median(local)),2) if local.size else None,
   "off_by_more_than_2_semitones":round(float(np.mean(local>2)),3) if local.size else None,
   "off_by_more_than_5_semitones":round(float(np.mean(local>5)),3) if local.size else None})
 jumps=0
 voiced_idxs=np.where(actual[:-1]&actual[1:])[0]
 if len(voiced_idxs):
  cents=np.abs(1200*np.log2(y[voiced_idxs+1]/y[voiced_idxs]))
  jumps=int((cents>500).sum())
 summary[name]={
   "frames":len(seq),"voiced_fraction":round(float(actual.mean()),3),
   "source_voiced_missing_fraction":round(float(np.mean(~actual[expected])),3) if expected.any() else None,
   "overall_voiced_pitch_median_semitones":round(float(np.median(delta[both])),2) if both.any() else None,
   "overall_voiced_pitch_median_absolute_error_semitones":round(float(np.median(np.abs(delta[both]))),2) if both.any() else None,
   "overall_fraction_off_by_more_than_2_semitones":round(float(np.mean(np.abs(delta[both])>2)),3) if both.any() else None,
   "overall_fraction_off_by_more_than_5_semitones":round(float(np.mean(np.abs(delta[both])>5)),3) if both.any() else None,
   "frame_octave_jump_gt_500cents_count":jumps,
   "five_second_windows":detail
 }
print("QA63_METRICS",json.dumps(summary,ensure_ascii=True),flush=True)
report={"note":"Extracted singing F0 contour at 100Hz with same RMVPE model on all source and conversions; no perceptual sound quality conclusion.","data":summary,"user_eval_QA62":"rejected"}
(D/"qa63_f0_pitch_timeline.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
np.savez_compressed(D/"qa63_F0_traces.npz",**f0)

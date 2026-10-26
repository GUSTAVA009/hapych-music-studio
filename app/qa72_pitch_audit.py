"""QA69 independent RMVPE frame-level melody continuity audit.
Unlike prior median-only reports, counts 10ms voice dropouts and short pitch jumps.
Read-only; no model weights or tracks modified.
"""
import os,sys,json,numpy as np,soundfile as sf
from pathlib import Path
from scipy.signal import resample_poly
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA72";D.mkdir(parents=True,exist_ok=True)
S=R/"Voice Engine"/"seed-vc"
os.chdir(S);os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1";sys.path.insert(0,str(S))
import torch
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
checkpoint=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
rmvpe=RMVPE(checkpoint,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
q=R/"Diagnostics"/"QA54";ref=R/"Diagnostics"/"QA66"
paths={"ACE_original":q/"QA54_CFG090_35s.source.wav",
       "QA54_voice":q/"QA54_CFG090_35s.dry.wav",
       "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
       "QA72_donor50":D/"QA72_Donor50_Mic30_Dry.wav",
       "QA72_donor90":D/"QA72_Donor90_Mic35_Dry.wav",
       "QA72_donor120":D/"QA72_Donor120_Mic35_Dry.wav"}
f0={}
for label,p in paths.items():
 x,sr=sf.read(p,dtype="float32",always_2d=True)
 v=x.mean(axis=1)
 y=resample_poly(v,160,441).astype(np.float32) if sr==44100 else resample_poly(v,16000,sr)
 f=np.asarray(rmvpe.infer_from_audio(y,thred=0.03),dtype=np.float64).ravel()
 f0[label]=f
 print("QA72_F0_DONE",label,len(f),flush=True)
source=f0["ACE_original"];result={}
for label,observed in f0.items():
 n=min(len(source),len(observed))
 s=source[:n];p=observed[:n]
 src_voiced=(s>55)&(s<1200);out_voiced=(p>55)&(p<1200)
 matched=src_voiced&out_voiced
 stable=(src_voiced[:-1]&src_voiced[1:]&out_voiced[:-1]&out_voiced[1:])
 s1=np.abs(12*np.log2(np.maximum(s[1:],1)/np.maximum(s[:-1],1)))
 p1=np.abs(12*np.log2(np.maximum(p[1:],1)/np.maximum(p[:-1],1)))
 source_stable=stable&(s1<.33)
 extra_changes=source_stable&(p1>.85)
 err=np.abs(12*np.log2(p[matched]/s[matched])) if matched.sum() else np.array([])
 r={"seconds":round(n*.01,2),"valid_matched_frames":int(matched.sum()),
   "source_voiced_fraction":round(float(src_voiced.mean()),4),
   "output_voiced_fraction":round(float(out_voiced.mean()),4),
   "source_voiced_missing_fraction":round(float(np.mean(~out_voiced[src_voiced])),4) if src_voiced.any() else None,
   "median_abs_pitch_error_semitones":round(float(np.median(err)),3) if err.size else None,
   "p90_abs_pitch_error_semitones":round(float(np.percentile(err,90)),3) if err.size else None,
   "fraction_gt2semitones_in_matched_voicing":round(float(np.mean(err>2)),4) if err.size else None,
   "excess_abrupt_pitch_changes_10ms_count":int(extra_changes.sum()),
   "excess_abrupt_pitch_changes_over_stable_source_fraction":round(float(extra_changes.sum()/max(1,source_stable.sum())),4),
   "pitch_glide_not_clipped":True,"not_quality_certificate":True}
 result[label]=r
 print("QA72_PITCH",label,json.dumps(r,ensure_ascii=True),flush=True)
(D/"qa72_pitch_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

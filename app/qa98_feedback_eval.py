"""QA98 compare both re-synthesized passes against the same source vocals.
Automated screen only; cannot certify human timbre or musical naturalness.
"""
from pathlib import Path
import json,os,sys
import soundfile as sf,numpy as np,torch
from math import gcd
from scipy.signal import resample_poly
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA98-F0Feedback';S=R/'Voice Engine'/'seed-vc'
sys.path.insert(0,str(S));sys.path.insert(0,str(R/'Voice Engine'))
os.chdir(S);os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache')
os.environ['HF_HUB_OFFLINE']='1'
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
from voice_guard42 import check
src=R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav'
choices={'baseline':D/'qa98_firstpass.wav','feedback':D/'qa98_feedback_candidate.wav'}
for f in (src,*choices.values()):assert f.exists(),f
model=RMVPE(load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None),
 is_half=False,device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
def contour(path):
 y,sr=sf.read(path,dtype='float32',always_2d=True);x=y.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
 return np.asarray(model.infer_from_audio(x,thred=.03),dtype='float64').ravel(),len(y)/sr
ref,refdur=contour(src)
report={}
for name,p in choices.items():
 f,dur=contour(p);n=min(len(f),len(ref))
 valid=(f[:n]>55)&(f[:n]<1200)&(ref[:n]>55)&(ref[:n]<1200)
 dif=1200*np.log2(f[:n][valid]/ref[:n][valid])
 stat=check(src,p,D/(name+'.voicecheck.json'),'ru')
 x={'p50_abs_cents':round(float(np.percentile(abs(dif),50)),2),
   'p75_abs_cents':round(float(np.percentile(abs(dif),75)),2),
   'p90_abs_cents':round(float(np.percentile(abs(dif),90)),2),
   'p95_abs_cents':round(float(np.percentile(abs(dif),95)),2),
   'fraction_gt35c':round(float(np.mean(abs(dif)>35)),4),
   'fraction_gt70c':round(float(np.mean(abs(dif)>70)),4),
   'voiced_match_frames':int(valid.sum()),
   'source_voiced_missing_fraction':round(float(np.mean(~((f[:n]>55)&(f[:n]<1200))[(ref[:n]>55)&(ref[:n]<1200)])),4),
   'source_duration_s':round(refdur,3),'out_duration_s':round(dur,3),
   'guard_status':stat['status'],
   'guard_accepted':bool(stat['accepted']),
   'missing_vocal_fraction':stat.get('metrics',{}).get('relative_missing_vocal_frames'),
   'energy_dips':stat.get('metrics',{}).get('energy_dip_events'),
   'audio_sha256':__import__('hashlib').sha256(p.read_bytes()).hexdigest(),
   'human_voice_identity_verified':False}
 report[name]=x
 print('QA98_F0_EVAL',name,json.dumps(x,ensure_ascii=True),flush=True)
a,b=report['baseline'],report['feedback']
p90gain=(a['p90_abs_cents']-b['p90_abs_cents'])/max(a['p90_abs_cents'],1)
pitch_ok=(b['p90_abs_cents']<=a['p90_abs_cents']*.85 and
     b['p50_abs_cents']<=a['p50_abs_cents']*1.03)
drop_ok=(b['guard_accepted'] and
 b['missing_vocal_fraction']<=a['missing_vocal_fraction']+.012 and
 b['source_voiced_missing_fraction']<=a['source_voiced_missing_fraction']+.015)
quality_gate=bool(pitch_ok and drop_ok)
report['decision']={'passes_preliminary_quantitative_gate':quality_gate,
                    'improvement_fraction_p90':round(p90gain,3),
                    'reason':'Pitch improvement and continuity' if quality_gate else 'Insufficient pitch improvement or worsened continuity',
                    'asr_not_yet_screened':True,'user_timbre_not_approved':True,
                    'production_pipeline_unchanged':True}
(D/'qa98_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('QA98_PRELIMINARY_GATE',json.dumps(report['decision'],ensure_ascii=True),flush=True)

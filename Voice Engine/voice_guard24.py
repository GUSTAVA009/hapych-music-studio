"""Screen measurable conversion regressions; never a studio-quality certificate.
Uses local cached ASR only when energy analysis finds suspicious losses.
No waveform replacement, no gates, no outside audio uploads.
"""
from pathlib import Path
import os,re,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter1d
ROOT=Path.home()/'Music Studio'
def edit_distance(a,b):
 row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  previous=row;row=[i]
  for j,y in enumerate(b,1):row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
 return row[-1]
def words(text):return re.findall(r'[^\W\d_]+',str(text).casefold().replace('ё','е'),flags=re.U)
def energy(source,converted):
 import soundfile as sf
 from scipy.signal import resample_poly
 from math import gcd
 def load(p):
  x,sr=sf.read(p,dtype='float32',always_2d=True)
  if sr!=16000:g=gcd(sr,16000);x=resample_poly(x,16000//g,sr//g,axis=0)
  return x
 a=load(source);b=load(converted);duration_error=(len(b)-len(a))/16000;length=min(len(a),len(b));hop=320
 def rms(x):
  n=len(x)//hop*hop;return np.sqrt(np.mean(x[:n].reshape(-1,hop,x.shape[1]).astype('float64')**2,axis=(1,2))+1e-12)
 ra,rb=rms(a[:length]),rms(b[:length]);active=ra>max(.003,float(np.percentile(ra,85))*.25)
 if active.sum()<25:return {'reliable':False,'reason':'too_little_active_source','duration_error':duration_error}
 level=np.median(20*np.log10((ra[active]+1e-9)/(rb[active]+1e-9)));relative=20*np.log10((rb+1e-9)/(ra+1e-9))+level
 mask=(relative < -10)&active;edges=np.diff(np.r_[False,mask,False].astype('int8'));segments=[]
 for start,end in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
  if end-start>=3:segments.append({'start':round(start*.02,3),'end':round(end*.02,3),'minimum_relative_db':round(float(relative[start:end].min()),2)})
 return {'reliable':True,'duration_error':round(duration_error,4),'active_frames':int(active.sum()),'drop_frames':int(mask.sum()),'drop_segments':segments,'analysis_seconds':length/16000}
def transcriptions(source,converted,language):
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
 import torch
 from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
 assets=ROOT/'Diagnostics'/'rejected-light-audit'/'whisper_text_assets';cache=ROOT/'Voice Engine'/'seed-vc'/'checkpoints'/'hf_cache'/'models--openai--whisper-small'/'snapshots'/'973afd24965f72e36ca33b3055d56a652f456b4d'
 if not assets.is_dir() or not cache.is_dir():raise FileNotFoundError('Local ASR assets unavailable; no download attempted')
 torch.set_num_threads(3);processor=AutoProcessor.from_pretrained(str(assets),local_files_only=True);model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval();model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True);model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
 result=[]
 for path in (source,converted):
  p=subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(path),'-t','24','-ac','1','-ar','16000','-f','f32le','pipe:1'],capture_output=True,check=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  x=np.frombuffer(p.stdout,dtype='<f4').copy();inputs=processor(x,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
  kwargs={'language':language} if language and language!='unknown' else {}
  with torch.inference_mode():tokens=model.generate(**inputs,task='transcribe',do_sample=False,num_beams=1,max_new_tokens=160,**kwargs)
  result.append(processor.batch_decode(tokens,skip_special_tokens=True)[0])
 return result

def check(source,converted,report_path,language='unknown'):
 measure=energy(source,converted);report={'status':'not_flagged','accepted':True,'energy':measure,'perceptual_quality_verified':False,'meaning':'No detected severe regression is not proof of natural singing.'}
 if abs(measure.get('duration_error',0))>.15:
  report.update(status='rejected',accepted=False,reason='Перенос голоса нарушил длину вокальной дорожки.')
 elif measure.get('reliable') and len(measure['drop_segments'])>=2:
  try:
   before,after=transcriptions(source,converted,language);a,b=words(before),words(after);distance=edit_distance(a,b);fraction=distance/max(len(a),1)
   report.update(asr_source=before,asr_converted=after,asr_edit_distance=distance,asr_difference=round(fraction,4),asr_checked_seconds=24)
   if len(a)>=10 and distance>=5 and fraction>.22 and len(measure['drop_segments'])>=3:
    report.update(status='rejected',accepted=False,reason='После переноса появились провалы и заметные изменения слов. Оставлен исходный певец, это не твой голос.')
   else:report.update(status='warning',reason='Есть подозрительные провалы; автоматическая проверка не подтверждает качество вокала.')
  except Exception as exc:report.update(status='unverified',reason='Проверка разборчивости не завершилась: '+str(exc)[:140])
 Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report

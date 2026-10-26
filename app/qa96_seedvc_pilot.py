"""QA96 independent personal Seed-VC diffusion/CFG sweep.

Reuses existing user-owned mic recording and personal trained checkpoint.
Same original 35s vocals as QA54. Never changes production config,
reference library, music tracks or checkpoints. Refuses if studio busy.
"""
from pathlib import Path
import sys,os,time,json,subprocess,requests
import numpy as np
ROOT=Path.home()/'Music Studio'
D=ROOT/'Diagnostics'/'QA96-SmoothPersonal'
D.mkdir(parents=True,exist_ok=True)
VE=ROOT/'Voice Engine';S=VE/'seed-vc';sys.path.insert(0,str(VE))
from convert_track_studio83 import reference_excerpt
recording=ROOT/'Мой голос'/'20261022_234327_Микрофон_3867cb.wav'
source=ROOT/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav'
model=S/'runs'/'alex_clean_qa44_v2'/'ft_model.pth'
config=S/'runs'/'alex_clean_qa44_v2'/'config_dit_mel_seed_uvit_whisper_base_f0_44k.yml'
py=VE/'.venv'/'Scripts'/'python.exe'
for p in (recording,source,model,config,py):assert p.is_file(),p
state=requests.get('http://127.0.0.1:7870/api/status',timeout=8).json()
assert state['status'] in ('idle','done','error'),'User generation in progress'
ref,meta=reference_excerpt(recording,D)
assert 17<=meta['seconds']<=22 and meta['total_recording_seconds']>30
print('QA96_REUSED_USER_REF',json.dumps({k:v for k,v in meta.items() if k not in ('source',)},ensure_ascii=True),flush=True)
cases=[
 ('cfg070_steps48',0.7,48),
 # CFG .90/steps40 established historical baseline QA54 (do NOT regenerate).
]
report={'study':'QA96','basis':'QA54 personal source same song and recording',
'baseline':str(ROOT/'Diagnostics'/'QA54'/'QA54_CFG090_35s.dry.wav'),
'production_modified':False,'new_artists_or_recordings':False,
'run_register':'original','pitch_shift':0,'source':str(source),
'reference_excerpt':meta,'cases':[]}
for name,cfg,steps in cases:
 if requests.get('http://127.0.0.1:7870/api/status',timeout=8).json()['status'] not in ('idle','done','error'):
  print('QA96_CANCELLED_STUDIO_BUSY',flush=True);break
 target=D/name;target.mkdir(exist_ok=True)
 cmd=[str(py),'-u','inference_studio51.py',
 '--source',str(source),'--target',str(ref),'--output',str(target),
 '--diffusion-steps',str(steps),'--inference-cfg-rate',str(cfg),
 '--f0-condition','True','--fp16','True','--auto-f0-adjust','False',
 '--semi-tone-shift','0','--register','original','--seed','74191',
 '--acoustic-prompt-seconds','18.0','--checkpoint',str(model),'--config',str(config)]
 env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_CACHE=str(S/'checkpoints'/'hf_cache'),
  PYTHONIOENCODING='utf-8',PYTHONUTF8='1',TOKENIZERS_PARALLELISM='false')
 t=time.monotonic();log=target/'inference_log.txt'
 print('QA96_RUN_START',name,flush=True)
 with log.open('w',encoding='utf8') as f:
  p=subprocess.Popen(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env)
  try:ret=p.wait(timeout=750)
  except subprocess.TimeoutExpired:
   p.kill();p.wait();ret=999
 dest=list(target.glob('vc_*.wav'))
 q={'name':name,'cfg':cfg,'steps':steps,'return_code':ret,'wall_seconds':round(time.monotonic()-t,1),'pitch_shift':0,'candidate':str(dest[0]) if dest else None,
    'status':'generated' if ret==0 and len(dest)==1 else 'failed',
    'log_tail':log.read_text(encoding='utf8',errors='replace')[-500:]}
 report['cases'].append(q)
 print('QA96_RUN_RESULT',json.dumps(q,ensure_ascii=True),flush=True)
 (D/'qa96_generation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 if q['status']!='generated':raise RuntimeError(name+' '+q['log_tail'][-250:])

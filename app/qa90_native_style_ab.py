"""QA90: Reproduce the owner's real last 70s dance-pop request, with NO forced
trained 808/reference audio. Compare to the original same-seed take. Read only
library, write Diagnostics. Does not alter Music Studio models, tracks, profiles.
"""
from pathlib import Path
import os,sys,json,hashlib,time,subprocess,requests,shutil
from gradio_client import Client
ROOT=Path.home()/'Music Studio'
JOB='81490cbc66914855bf58a7bcc7f3ae8a'
REQ=json.loads((ROOT/'app'/'requests'/(JOB+'.json')).read_text(encoding='utf-8'))
VAR=json.loads((ROOT/'app'/'requests'/(JOB+'_variants.json')).read_text(encoding='utf-8'))[0]
OUT=ROOT/'Diagnostics'/'QA90-NativeStyle';OUT.mkdir(parents=True,exist_ok=True)
ENGINE='http://127.0.0.1:7862'
def status():
 return requests.get('http://127.0.0.1:7870/api/status',timeout=8).json()['status']
assert status() in ('done','idle','error')
cfg=requests.get(ENGINE+'/config',timeout=10).json()
comps={c['id']:c for c in cfg['components']}
dep=next(x for x in cfg['dependencies'] if x.get('api_name')=='generation_wrapper')
v=dict(VAR['settings'])
v.pop('Reference Audio',None)
v['Key']=REQ['settings'].get('Key') or ''
v['Time Signature']=REQ['settings'].get('Time Signature') or ''
v['Music Caption']=REQ['settings']['Music Caption']
v['Batch Size']=1
v['Random Seed']=False
v['Seed']=str(VAR['seed'])
v['Auto Score']=False
v['Auto LRC']=False
v['__test_no_automatic_reference']=True
assert int(v['BPM (Beats Per Minute)'])==130 and int(v['Audio Duration (seconds)'])==70
assert not v['Key']
args=[]
for cid in dep['inputs']:
 comp=comps[cid]
 if comp['type']=='state':continue
 prop=comp.get('props',{})
 args.append(v.get(prop.get('label'),prop.get('value')))
assert len(args)==72,len(args)
info={'experiment':'QA90 native style without forced beat reference',
 'source_request':JOB,'seed':VAR['seed'],'original_reference':VAR.get('reference',{}).get('path'),
 'caption':v['Music Caption'],'model':'acestep-v15-turbo',
 'keep_original_unchanged':True,'style_reference_removed':True,'new_key_forced':False,'status':'running'}
start=time.monotonic()
try:
 print('QA90_BEGIN',VAR['seed'],'source_ref',info['original_reference'],flush=True)
 client=Client(ENGINE,verbose=False)
 client.predict(False,api_name='/set_use_lora')
 job=client.submit(*args,api_name='/generation_wrapper')
 while not job.done():
  if time.monotonic()-start>600:
   job.cancel();raise TimeoutError('QA90 took >600s')
  if status() in ('preparing','generating','converting'):
   job.cancel();raise RuntimeError('User triggered a new generation; cancelled QA90')
  time.sleep(2)
 reply=job.result()
 out_ids=[cid for cid in dep['outputs'] if not comps[cid].get('skip_api',comps[cid]['type']=='state')]
 vals={comps[cid].get('props',{}).get('label'):p for cid,p in zip(out_ids,reply)}
 audio=vals.get('🎵 Generated Music (Sample 1)')
 if isinstance(audio,dict):audio=audio.get('value',audio.get('path'))
 if not isinstance(audio,str) or not Path(audio).is_file():
  audio=next((a.get('value') if isinstance(a,dict) else a for a in reply
    if isinstance(a,str) and a.lower().endswith(('.wav','.mp3','.flac')) and Path(a).is_file()
    or isinstance(a,dict) and isinstance(a.get('value'),str) and a['value'].endswith(('.wav','.mp3')) and Path(a['value']).is_file()),None)
 if not audio:raise RuntimeError('No audio in engine response')
 original=Path(audio)
 dst=OUT/'no_reference_70s.wav'
 shutil.copy2(original,dst)
 with (OUT/'no_reference_70s.mp3').open('wb') as f:
  enc=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(dst),'-c:a','libmp3lame','-b:a','320k','pipe:1'],
      stdout=f,stderr=subprocess.PIPE,timeout=80)
 if enc.returncode:raise RuntimeError('MP3 encoder failed:'+enc.stderr.decode('utf8','replace')[-250:])
 from audio_guard55 import inspect_source
 info.update(status='finished_experimental',audio=str(dst), mp3=str(OUT/'no_reference_70s.mp3'),
  dc_check=inspect_source(dst),sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
  elapsed_s=round(time.monotonic()-start,2))
 print('QA90_NEW_AUDIO_READY',json.dumps({'duration':70,'seed':info['seed'],'mp3':info['mp3'],
       'elapsed_s':info['elapsed_s'],'reference_audio':False},ensure_ascii=True),flush=True)
except Exception as exc:
 info.update(status='failed',error=repr(exc))
 print('QA90_ERROR',repr(exc),flush=True)
finally:
 (OUT/'qa90_run_report.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')

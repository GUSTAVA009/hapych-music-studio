"""QA86 controlled ACE-Step SFT vs Turbo Russian articulatory benchmark.

It never edits studio settings, user tracks or uploaded recordings.
Both renders use the same prompt, lyrics, seed and duration with architecture-
appropriate official inference steps. Run ONE variant per invocation.
"""
from pathlib import Path
from gradio_client import Client
import argparse,hashlib,json,shutil,time,requests,traceback,sys
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA86-SFTBenchmark';D.mkdir(parents=True,exist_ok=True)
PROMPT=("Russian upbeat dance-pop, 120 BPM. Confident natural warm male baritone, "
 "continuous legato Russian singing, native accent, crisp clear syllables, "
 "fully pronounced stressed vowels and complete consonant word endings. "
 "Bouncy 808 bass, groovy punchy kick, bright funky piano, claps. "
 "Clean vocal with no female voices, no robotic stutters, no exaggerated vibrato.")
LYRICS="""[Verse]
Ты меня тихо найдёшь,
Все слова произнесёшь.
Снова рядом подойдёшь,
Песню мне одну споёшь.

[Chorus]
Ты найдёшь, ты найдёшь,
И меня ты позовёшь.
Дай, дай, дай мне ладонь,
Снова музыка, огонь!

[Outro]
Ты меня найдёшь.
"""
def status():
 return requests.get('http://127.0.0.1:7870/api/status',timeout=9).json().get('status')
def test(name,port):
 if status() not in ('idle','done','error'):
  raise RuntimeError('Studio currently generating: benchmark must not compete')
 url='http://127.0.0.1:'+str(port)
 conf=requests.get(url+'/config',timeout=20).json()
 comps={c['id']:c for c in conf['components']}
 deps=[x for x in conf['dependencies'] if x.get('api_name')=='generation_wrapper']
 assert len(deps)==1
 loaded=next((c['props'].get('value') for c in conf['components'] if c.get('props',{}).get('label')=='Main Model Path'),'unknown')
 if name=='sft' and 'sft' not in loaded:raise RuntimeError('Expected SFT UI config; got '+str(loaded))
 if name=='turbo' and 'turbo' not in loaded:raise RuntimeError('Expected Turbo UI config; got '+str(loaded))
 v={
  'Music Caption':PROMPT,'Lyrics':LYRICS,
  'Audio Duration (seconds)':35,'BPM (Beats Per Minute)':120,
  'Batch Size':1,'Vocal Language':'ru','Random Seed':False,
  'Seed':'7813095','DiT Inference Steps':50 if name=='sft' else 8,
  'DiT Guidance Scale (Base model only)':7.0,
  'Shift':1.0 if name=='sft' else 3.0,
  'LM Temperature':0.75,'LM Batch Chunk Size':1,'LM Codes Hints':'',
  'LM Negative Prompt':'foreign-accented Russian, dropped word endings, robotic vowel chopping, clipped consonants, falsetto, synthetic vibrato',
  'CoT Metas (Chain-of-Thought Metadata)':True,'CoT Language Detection':False,
  'Think':True,'CaptionRewrite':False,'Auto LRC':False,'Auto Score':False,
  'Audio Format':'wav','MP3 Bitrate':'320k'
 }
 args=[]
 for cid in deps[0]['inputs']:
  comp=comps[cid]
  if comp['type']=='state':continue
  p=comp.get('props',{})
  args.append(v.get(p.get('label'),p.get('value')))
 assert len(args)==72,len(args)
 record={'name':name,'engine_port':port,'model':loaded,'fixed_seed':'7813095',
         'caption':PROMPT,'lyrics':LYRICS,'settings':v,'duration_requested':35,
         'changed_user_music':False,'human_perceptual_verification':False}
 start=time.monotonic()
 try:
  client=Client(url,verbose=False)
  client.predict(False,api_name='/set_use_lora')
  job=client.submit(*args,api_name='/generation_wrapper')
  while not job.done():
   if time.monotonic()-start>900:
    job.cancel();raise TimeoutError('Benchmark exceeded 900 seconds')
   try: current=status()
   except Exception: current='unknown'
   if current in ('preparing','generating','converting'):
    job.cancel();raise RuntimeError('User triggered studio generation; benchmark cancelled')
   time.sleep(2)
  answer=job.result()
  outputs=[i for i in deps[0]['outputs'] if not comps[i].get('skip_api',comps[i]['type']=='state')]
  values={comps[i].get('props',{}).get('label'):value for i,value in zip(outputs,answer)}
  audio=values.get('🎵 Generated Music (Sample 1)')
  if isinstance(audio,dict):audio=audio.get('value',audio.get('path'))
  if not isinstance(audio,str) or not Path(audio).is_file():
   audio=next((x.get('value') if isinstance(x,dict) else x for x in answer if isinstance(x,str) and x.endswith(('.wav','.flac','.mp3')) or isinstance(x,dict) and isinstance(x.get('value'),str) and x.get('value').endswith(('.wav','.flac','.mp3'))),None)
  if not audio or not Path(audio).is_file():raise RuntimeError('Engine returned no audio path')
  dst=D/(name+'_35s'+Path(audio).suffix.lower())
  shutil.copy2(audio,dst)
  record.update(status='generated_experimental',filename=str(dst),size=dst.stat().st_size,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
    elapsed_s=round(time.monotonic()-start,2),
    quality_score=str(values.get('Quality Score (Sample 1)',''))[:600],
    lrc=str(values.get('Lyrics Timestamps (Sample 1)',''))[:5000])
  print('QA86_COMPLETE '+json.dumps({k:v for k,v in record.items() if k not in ('lyrics','caption','settings','lrc')},ensure_ascii=True),flush=True)
 except Exception as e:
  record.update(status='failed',error=repr(e)[:1000])
  traceback.print_exc();print('QA86_FAILED '+name+' '+repr(e),flush=True)
 finally:
  (D/(name+'_report.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--name',choices=['sft','turbo'],required=True)
 a=p.parse_args()
 test(a.name,7864 if a.name=='sft' else 7862)

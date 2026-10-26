"""Two independently composed takes; bounded calls, explicit fresh seeds and traceable plans."""
from pathlib import Path
import hashlib,json,secrets,time
from gradio_client import Client,handle_file
from arrangement24 import make_reference,needs_808

ROOT=Path.home()/'Music Studio';HISTORY=ROOT/'app'/'arrangement21-history.json'
def fresh_seeds(style,count):
 key=hashlib.sha256(str(style).encode()).hexdigest();history={}
 if HISTORY.is_file():
  try:history=json.loads(HISTORY.read_text(encoding='utf-8'))
  except (OSError,ValueError):pass
 used=[tuple(p) for p in history.get(key,[])][-4:];seeds=[]
 for _ in range(count):
  for attempt in range(100):
   seed=secrets.randbelow(2147483646)+1;pair=(seed%6,(seed//7)%6)
   if pair not in used and (not seeds or seed%6!=seeds[0]%6 and (seed//7)%6!=(seeds[0]//7)%6):break
  else:raise RuntimeError('Could not create independent musical seeds')
  seeds.append(seed);used.append(pair)
 history[key]=used[-4:]
 # Keep a small bounded history; no user lyrics or voice data are stored here.
 history=dict(list(history.items())[-128:]);HISTORY.parent.mkdir(exist_ok=True)
 tmp=HISTORY.with_suffix('.tmp');tmp.write_text(json.dumps(history),encoding='utf-8');tmp.replace(HISTORY)
 return seeds

def compose(settings,config,style,mode,engine_url,job_id,on_stage,client_factory=Client):
 components={c['id']:c for c in config['components']};dep=next(d for d in config['dependencies'] if d.get('api_name')=='generation_wrapper')
 count=int(settings.get('Batch Size',1));seeds=fresh_seeds(style,count);paths=[];timestamps={};records=[];digests=[]
 client=client_factory(engine_url,verbose=False);client.predict(False,api_name='/set_use_lora')
 for index,seed in enumerate(seeds,1):
  v=dict(settings);v.update({'Batch Size':1,'Random Seed':False,'Seed':str(seed),'LM Codes Hints':'','LM Temperature':.90 if index==1 else .95,'LM Batch Chunk Size':1})
  ref=None
  if mode!='remix' and not v.get('Reference Audio') and needs_808(style):
   ref=make_reference(style,v.get('BPM (Beats Per Minute)') or 0,v.get('Key',''),seed)
   if ref:
    v['Reference Audio']=handle_file(ref['path']);v['Key']=ref['reference_key'];v['BPM (Beats Per Minute)']=int(round(ref['bpm']));v['Time Signature']='4'
    harmony='Key '+ref['reference_key']+'; chords '+' - '.join(c['name'] for c in ref['plan']['chords'])
    if len(v['Music Caption'])+len(harmony)+2<=512:v['Music Caption']+='; '+harmony
  on_stage('Вариант %d/%d: создаём отдельную композицию и ритм…'%(index,count))
  arguments=[]
  for cid in dep['inputs']:
   c=components[cid]
   if c['type']=='state':continue
   prop=c.get('props',{});arguments.append(v.get(prop.get('label'),prop.get('value')))
  if len(arguments)!=72:raise RuntimeError('Изменился интерфейс музыкального движка; генерация остановлена безопасно.')
  began=time.monotonic();task=client.submit(*arguments,api_name='/generation_wrapper')
  while not task.done():
   if time.monotonic()-began>1800:
    try:task.cancel()
    except Exception:pass
    raise TimeoutError('Музыкальный движок превысил допустимое время обработки.')
   time.sleep(.5)
  reply=task.result();out_ids=[cid for cid in dep['outputs'] if not components[cid].get('skip_api',components[cid]['type']=='state')]
  values={components[cid].get('props',{}).get('label'):value for cid,value in zip(out_ids,reply)}
  audio=values.get('🎵 Generated Music (Sample 1)')
  if isinstance(audio,dict):audio=audio.get('value',audio.get('path'))
  if not isinstance(audio,str) or not Path(audio).is_file():
   candidates=[]
   for value in reply:
    value=value.get('value') if isinstance(value,dict) else value
    if isinstance(value,str) and value.lower().endswith(('.wav','.flac','.mp3')) and Path(value).is_file():candidates.append(value)
   if not candidates:raise RuntimeError('Музыкальный движок не вернул звуковой файл варианта %d.'%index)
   audio=candidates[0]
  fingerprint=hashlib.sha256(Path(audio).read_bytes()).hexdigest()
  if fingerprint in digests:raise RuntimeError('Движок вернул идентичный аудиофайл для разных seed; дубликат не принят как второй вариант.')
  digests.append(fingerprint);paths.append(audio)
  lrc=values.get('Lyrics Timestamps (Sample 1)','');lrc=lrc.get('value','') if isinstance(lrc,dict) else lrc;timestamps[index]=lrc if isinstance(lrc,str) else ''
  record={'variant':index,'seed':seed,'elapsed_seconds':round(time.monotonic()-began,2),'settings':{k:value for k,value in v.items() if k not in ('Reference Audio','Source Audio')},'reference':ref,'sha256':fingerprint,'source_file':audio}
  records.append(record)
 return paths,timestamps,records

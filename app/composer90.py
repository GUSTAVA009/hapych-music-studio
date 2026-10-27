"""Music Studio QA90 composer: user style first, optional sample-based guide.

Do not inject synthetic Reference Audio or silently force a generated key
when user did not explicitly enable groove guidance.
"""
from pathlib import Path
import hashlib,json,secrets,time
from gradio_client import Client,handle_file
from arrangement25 import make_reference
from groove_preflight import availability, GrooveReferenceUnavailable

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
  v=dict(settings);v.update({'Batch Size':1,'Random Seed':False,'Seed':str(seed),'LM Codes Hints':'','LM Temperature':.78 if index==1 else .83,'LM Batch Chunk Size':1})
  ref=None
  groove_warning=None
  # QA90: optional, user-directed groove reference ONLY. A text request
  # for deep 808 bass is not consent to replace song conditioning with
  # an eight-bar artificial demo loop or to force an arbitrary minor key.
  optional_groove=bool(settings.get('__use_trained_groove_reference',False))
  if mode!='remix' and optional_groove and not v.get('Reference Audio') and settings.get('__style_plan',{}).get('reference_policy')=='trained_808':
   groove_state=availability(ROOT)
   if not groove_state['available']:
    groove_warning=groove_state['message']
   else:
    try:
     ref=make_reference(style,v.get('BPM (Beats Per Minute)') or 0,v.get('Key',''),seed)
    except (GrooveReferenceUnavailable, FileNotFoundError, OSError, RuntimeError, ValueError, ImportError) as failure:
     groove_warning=('Экспериментальная модель 808-грува не смогла создать подложку '
                     '('+type(failure).__name__+'). Генерация продолжается без обученного грува.')
   if groove_warning:
    on_stage(groove_warning)
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
  # Retry only an invalid take, not the whole batch. Never publish DC-dominated noise.
  from audio_guard55 import inspect_source
  try:
   inspect_source(audio)
  except RuntimeError as failure:
   on_stage('Вариант %d/%d: обнаружен брак аудио; автоматически пробуем другой seed один раз…'%(index,count))
   old_seed=seed
   seed=fresh_seeds(style,1)[0]
   if seed==old_seed:
    seed=(seed%2147483646)+1
   v['Seed']=str(seed)
   retry_args=[]
   for cid in dep['inputs']:
    c=components[cid]
    if c['type']=='state':continue
    prop=c.get('props',{})
    retry_args.append(v.get(prop.get('label'),prop.get('value')))
   if len(retry_args)!=72:raise RuntimeError('Конфигурация движка изменилась; повтор отменён.')
   retry_started=time.monotonic()
   retry_task=client.submit(*retry_args,api_name='/generation_wrapper')
   while not retry_task.done():
    if time.monotonic()-retry_started>1800:
     try:retry_task.cancel()
     except Exception:pass
     raise TimeoutError('Повторная генерация превысила 30 минут.')
    time.sleep(.5)
   retry_reply=retry_task.result()
   retry_values={components[cid].get('props',{}).get('label'):value for cid,value in zip(out_ids,retry_reply)}
   retry_audio=retry_values.get('🎵 Generated Music (Sample 1)')
   if isinstance(retry_audio,dict):retry_audio=retry_audio.get('value',retry_audio.get('path'))
   if not isinstance(retry_audio,str) or not Path(retry_audio).is_file():
    choices=[]
    for value in retry_reply:
     value=value.get('value') if isinstance(value,dict) else value
     if isinstance(value,str) and value.lower().endswith(('.wav','.flac','.mp3')) and Path(value).is_file():choices.append(value)
    if not choices:raise RuntimeError('Повторный запуск не вернул WAV/MP3.')
    retry_audio=choices[0]
   try:inspect_source(retry_audio)
   except RuntimeError as second:
    raise RuntimeError('Музыкальный движок дважды вернул бракованный звук. Трек не опубликован; перезапусти ACE-Step.') from second
   audio=retry_audio
   values=retry_values
   began=retry_started
  fingerprint=hashlib.sha256(Path(audio).read_bytes()).hexdigest()
  if fingerprint in digests:raise RuntimeError('Движок вернул идентичный аудиофайл для разных seed; дубликат не принят как второй вариант.')
  digests.append(fingerprint);paths.append(audio)
  lrc=values.get('Lyrics Timestamps (Sample 1)','');lrc=lrc.get('value','') if isinstance(lrc,dict) else lrc;timestamps[index]=lrc if isinstance(lrc,str) else ''
  record={'prompt_plan':settings.get('__style_plan',{}),'variant':index,'seed':seed,'elapsed_seconds':round(time.monotonic()-began,2),'settings':{k:value for k,value in v.items() if k not in ('Reference Audio','Source Audio')},'reference':ref,'reference_source':('explicit_groove_opt_in' if ref else 'optional_groove_unavailable' if groove_warning else 'user_supplied' if v.get('Reference Audio') else 'none'),'groove_reference_warning':groove_warning,'automatic_minor_key_forced':bool(ref),'sha256':fingerprint,'source_file':audio}
  records.append(record)
 return paths,timestamps,records

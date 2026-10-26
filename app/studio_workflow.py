"""One local workflow using the already installed music LM, no new model downloads."""
from __future__ import annotations
import copy,json,re,threading,time,uuid,subprocess,wave,math
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import requests
from gradio_client import Client
from studio_sections import compile_sections

ROOT=Path(__file__).resolve().parent.parent
HISTORY=ROOT/'Мои тексты';HISTORY.mkdir(exist_ok=True)
LATEST=HISTORY/'latest.json'
_LOCK=threading.RLock()
_state={'id':None,'status':'idle','message':'Задай тему и стиль','variants':[],'error':''}
if LATEST.is_file():
    try:
        saved=json.loads(LATEST.read_text(encoding='utf-8'))
        if saved.get('status')=='done' and len(saved.get('variants',[]))==2 and all(v.get('quality',{}).get('passed') for v in saved['variants']):_state=saved
    except (OSError,ValueError):pass

def lyric_status():
    with _LOCK:return copy.deepcopy(_state)

def lyrics_active():
    with _LOCK:return _state['status'] in ('preparing','generating')

def validate_topic(data):
    if not isinstance(data,dict):raise ValueError('Нужны тема и стиль.')
    topic=str(data.get('topic','')).strip();style=str(data.get('style','')).strip()
    if not topic:raise ValueError('Укажи, о чём будет песня.')
    if not style:raise ValueError('Укажи музыкальный стиль.')
    if len(topic)>1200 or len(style)>3000:raise ValueError('Тема: до 1200 символов; стиль: до 3000.')
    from lyric_writer16 import detect_language
    language=detect_language(topic,detect_language(style))
    if language not in ('ru','en','auto'):raise ValueError('Неподдерживаемый язык текста.')
    gender='auto'
    if gender not in ('auto','female','male'):raise ValueError('Неверный тип вокала.')
    return dict(topic=topic,style=style,vocal_language='ru' if language=='auto' else language,vocal_gender=gender)

def reserve_lyrics(data):
    normalized=validate_topic(data)
    with _LOCK:
        if lyrics_active():raise RuntimeError('Два варианта уже создаются.')
        _state.update(id=uuid.uuid4().hex,status='preparing',message='Подготавливаем два варианта текста...',error='',request=normalized)
        return _state['id'],normalized

def _change(**kwargs):
    with _LOCK:_state.update(kwargs)

def _sample_endpoint(config):
    cs={c['id']:c for c in config['components']};candidates=[]
    for dep in config['dependencies']:
        ins=[cs[i] for i in dep.get('inputs',[]) if cs[i]['type']!='state']
        outs=[cs[i].get('props',{}).get('label') for i in dep.get('outputs',[])]
        if len(ins)==7 and outs[:2]==['Music Caption','Lyrics']:candidates.append(dep['api_name'])
    if len(candidates)!=1:raise RuntimeError('Интерфейс генерации текста изменился; рабочие песни не затронуты.')
    return '/'+candidates[0]

def write_lyrics(data,job_id,ensure_engine,engine_url):
    from lyric_writer17 import create_pair
    started=time.monotonic()
    try:
        variants=create_pair(data,lambda message:_change(status='generating',message=message))
        _change(status='done',message='Готовы два черновика. Отредактируй и выбери один.',variants=variants,error='',elapsed_seconds=round(time.monotonic()-started,1))
        snapshot=lyric_status();serialized=json.dumps(snapshot,ensure_ascii=False,indent=2)
        (HISTORY/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+job_id+'.json')).write_text(serialized,encoding='utf-8')
        partial=LATEST.with_suffix('.tmp');partial.write_text(serialized,encoding='utf-8');partial.replace(LATEST)
    except Exception as exc:
        _change(status='error',message='Новая пара не готова; выбранный текст сохранён',error=str(exc))

def normalize_recording(source:Path,destination:Path):
    """Decode browser WebM/Opus to WAV. No denoising, pitch effects or cloud transfer."""
    flags=subprocess.CREATE_NO_WINDOW
    p=subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(source),'-map','0:a:0','-vn','-t','181',
                      '-ac','1','-ar','48000','-c:a','pcm_s16le',str(destination)],capture_output=True,timeout=60,creationflags=flags)
    if p.returncode or not destination.is_file():raise ValueError('Браузерную запись не удалось прочитать. Попробуй записать ещё раз.')
    with wave.open(str(destination),'rb') as audio:
        seconds=audio.getnframes()/audio.getframerate();frames=audio.readframes(audio.getnframes())
    if not 1.0<=seconds<=180.5:raise ValueError('Запись должна длиться от 1 секунды до 3 минут.')
    import array
    a=array.array('h',frames)
    peak=max((abs(v) for v in a),default=0)/32768
    rms=math.sqrt(sum((v/32768)**2 for v in a)/max(1,len(a)))
    warning=''
    if peak<0.003:raise ValueError('В записи почти тишина. Проверь выбранный микрофон.')
    if peak>0.99:warning='Есть перегрузка. Снизь уровень микрофона и перезапиши.'
    elif rms<0.008:warning='Тихая запись: поднеси микрофон ближе, не включая усиление с эффектами.'
    return {'seconds':round(seconds,2),'peak_dbfs':round(20*math.log10(max(peak,1e-9)),1),
            'rms_dbfs':round(20*math.log10(max(rms,1e-9)),1),'warning':warning}

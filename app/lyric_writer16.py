"""Local lyric author with bounded retries and explicit draft validation.
Not model training. CPU-only service; user text is never sent off this computer.
"""
from __future__ import annotations
import json,os,re,subprocess,threading,time,uuid
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher
import requests

ROOT=Path(__file__).resolve().parent.parent
ENGINE=ROOT/'Text Engine';URL='http://127.0.0.1:7872'
LOCK=threading.RLock();_proc=None

def detect_language(text:str,fallback='ru')->str:
    text=re.sub(r'\[[^\]]*\]','',str(text))
    ru=len(re.findall(r'[А-Яа-яЁё]',text));en=len(re.findall(r'[A-Za-z]',text))
    if ru+en<3:return fallback
    return 'ru' if ru/(ru+en)>=0.55 else 'en'

def session():
    s=requests.Session();s.trust_env=False;return s

def ensure_writer():
    global _proc
    with LOCK:
        try:
            r=session().get(URL+'/health',timeout=1)
            if r.status_code==200:return
        except requests.RequestException:pass
        manifest=ENGINE/'installation.json'
        if not manifest.is_file():raise RuntimeError('Текстовый движок ещё не установлен. Старый музыкальный генератор слов отключён.')
        conf=json.loads(manifest.read_text(encoding='utf-8'))
        cmd=[conf['executable'],'-m',conf['model'],'--host','127.0.0.1','--port','7872','-c','8192','-t','6','-tb','6','-ngl','0','--parallel','1','--no-webui','--jinja','--reasoning-budget','768','--reasoning-format','deepseek']
        if _proc is None or _proc.poll() is not None:
            with (ENGINE/'writer.log').open('ab') as log:
                _proc=subprocess.Popen(cmd,cwd=str(Path(conf['executable']).parent),stdout=log,stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(120):
            if _proc.poll() is not None:raise RuntimeError('Не запустился текстовый движок. См. Text Engine/writer.log.')
            try:
                if session().get(URL+'/health',timeout=1).status_code==200:return
            except requests.RequestException:pass
            time.sleep(.5)
        raise TimeoutError('Текстовый движок не загрузился.')

def complete(messages,max_tokens=2600,temperature=.70,thinking=True):
    response=session().post(URL+'/v1/chat/completions',json={
        'model':'local-writer','messages':messages,'temperature':temperature,'top_p':.9,
        'max_tokens':max_tokens,'repeat_penalty':1.05,'chat_template_kwargs':{'enable_thinking':thinking},'response_format':{'type':'json_object'}},timeout=(10,420))
    response.raise_for_status();result=response.json()
    if result['choices'][0].get('finish_reason')=='length':raise ValueError('Ответ автора превысил лимит; черновик не выдан как готовый.')
    text=(result['choices'][0]['message'].get('content') or '').strip()
    if not text:raise ValueError('Автор не вернул завершённый текст.')
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    return json.loads(text)

VOWELS='аеёиоуыэюя'
def syllables(line):return sum(c in VOWELS for c in line.casefold())
def ending(line):
    words=re.findall(r'[А-Яа-яЁё]+',line.casefold())
    if not words:return ''
    value=words[-1].replace('ё','е')
    devoiced={'б':'п','в':'ф','г':'к','д':'т','ж':'ш','з':'с'}
    return value[:-1]+devoiced.get(value[-1],value[-1])
def rhyme_hint(a,b):
    # Conservative spelling heuristic, not a phonetic or semantic guarantee.
    a,b=ending(a),ending(b)
    if not a or not b or a==b:return False
    for size in (4,3,2):
        tail=a[-size:]
        if len(tail)==size and tail==b[-size:] and any(v in tail for v in VOWELS):return True
    return False

def validate_draft(lyrics,language,topic=''):
    lines=[x.strip() for x in lyrics.splitlines() if x.strip()]
    sung=[x for x in lines if not x.startswith('[')]
    issues=[]
    if len(sung)<12 or len(sung)>40:issues.append('Нужно 12–40 законченных строк, а не короткий обрывок или длинные повторы.')
    if len(lyrics)>4096:issues.append('Текст длиннее 4096 символов.')
    if re.search(r'[А-Яа-яЁё][A-Za-z]|[A-Za-z][А-Яа-яЁё]',lyrics):issues.append('Склеенные кириллические и латинские части слов.')
    if language=='ru':
        latin=re.findall(r'\b[A-Za-z]{3,}\b',' '.join(sung))
        allowed=set(w.casefold() for w in re.findall(r'\b[A-Za-z]{3,}\b',topic))
        if any(w.casefold() not in allowed for w in latin):issues.append('Непрошенные английские слова в русском тексте.')
        if any(syllables(x)<4 or syllables(x)>20 for x in sung):issues.append('Есть слишком короткие/длинные строки: держи 7–13 слогов.')
    profanity=r'въеб|генитал|секс|пенис|вагин|ебал|бляд|хуй|пизд'
    if not re.search(profanity,topic,re.I) and re.search(profanity,' '.join(sung),re.I):issues.append('Непрошенная грубая или сексуальная тема.')
    if sum(len(x.split())<=2 for x in sung)>2:issues.append('Обрывки вместо законченных строк.')
    sections=[];current=[]
    for line in lines:
        if line.startswith('['):
            if current:sections.append(current)
            current=[]
        else:current.append(line)
    if current:sections.append(current)
    rhymed=total=0
    for section in sections:
        if len(section)%2:issues.append('Нечётное число строк в строфе; используй четверостишия.')
        for i in range(0,len(section)-1,2):
            total+=1
            rhymed+=int(rhyme_hint(section[i],section[i+1]))
            if language=='ru' and abs(syllables(section[i])-syllables(section[i+1]))>5:issues.append('Соседние строки сильно расходятся по длине.')
    if language=='ru' and total and rhymed/total<.8:issues.append('Слишком мало обнаружимых парных рифм. Перепиши окончания естественными рифмами ААББ.')
    counts=Counter(sung)
    if any(n>3 for n in counts.values()):issues.append('Одна строка повторена больше трёх раз.')
    return {'passed':not issues,'issues':list(dict.fromkeys(issues)),'line_count':len(sung),
        'rhyme_pairs_hint':rhymed,'pairs':total,'rhythm_check':'heuristic','language':language}

SYSTEM_RU='''Ты профессиональный русскоязычный автор песен. Пиши осмысленные, естественные и певучие строки, не случайную смесь слов. Сначала мысленно продумай один сюжет и окончания рифм, затем выдай только окончательный текст. Не копируй известные песни. Все слова должны существовать. Правильные падежи и согласование обязательны. Нельзя портить грамматику ради рифмы. Не используй бессмысленные английские вставки, технические слова и комментарии о генерации. Не добавляй секс, ругань или унижение, если этого не просили. Простая разговорная лексика, конкретные образы и связное развитие темы.
Верни строго JSON: {"variants":[{"title":"название","lyrics":"[Verse 1]\\n..."},{"title":"другое название","lyrics":"[Verse 1]\\n..."}]}.
В каждом варианте ровно 4 строфы по 4 строки: [Verse 1], [Chorus], [Verse 2], [Chorus]. Последний припев повторяет первый. В каждой строфе парная рифма ААББ (1 с 2, 3 с 4), приблизительно 8–12 слогов в строке. Не рифмуй слово само с собой. Пример естественной пары: «Мы у причала встретим май / Ладонь из рук не выпускай». Это пример, не включай его автоматически. Два варианта должны иметь разные образы и припевы, но оба строго по заданной теме. Не описывай инструменты в спетых строках, если это не тема песни. Никаких пояснений вне JSON.'''
SYSTEM_EN='''You are a professional songwriter. Return only JSON with exactly two variants: {"variants":[{"title":"Title","lyrics":"[Verse 1]\\n..."},{"title":"Other title","lyrics":"..."}]}. Each song has four four-line stanzas [Verse 1], [Chorus], [Verse 2], [Chorus]. Use meaningful narrative, natural English, singable meter and AABB rhymes. Repeat the chorus once. No random gibberish, unsolicited profanity or sexual content. Never copy existing songs. Two genuinely distinct perspectives on the user's theme.'''

def create_pair(data,on_stage):
    ensure_writer();language=detect_language(data['topic'],detect_language(data['style']))
    user='Тема: '+data['topic']+'\nМузыкальный стиль: '+data['style']+'\nСоздай два новых текста по этим условиям.'
    messages=[{'role':'system','content':SYSTEM_RU if language=='ru' else SYSTEM_EN},{'role':'user','content':user}]
    last_issues=[]
    for attempt in range(2):
        on_stage('Пишем два текста...' if attempt==0 else 'Редактируем рифмы, ритм и связность текста...')
        answer=complete(messages,temperature=.72 if attempt==0 else .55)
        entries=answer.get('variants',[]);results=[];last_issues=[]
        if len(entries)!=2:last_issues.append('Нужны ровно два варианта.')
        for index,item in enumerate(entries[:2]):
            lyric=str(item.get('lyrics','')).strip();audit=validate_draft(lyric,language,data['topic'])
            last_issues.extend(['Вариант %d: %s'%(index+1,s) for s in audit['issues']])
            results.append({'id':uuid.uuid4().hex,'title':str(item.get('title','Вариант '+str(index+1)))[:80],
                'lyrics':lyric,'topic':data['topic'],'style':data['style'],'vocal_language':language,'vocal_gender':'auto',
                'quality':audit,'writer':json.loads((ENGINE/'installation.json').read_text(encoding='utf-8')).get('author_label','Local lyric author'),'status':'editable_draft'})
        if len(results)==2 and SequenceMatcher(None,results[0]['lyrics'],results[1]['lyrics']).ratio()>.86:last_issues.append('Варианты слишком похожи, нужны разные сюжеты и припевы.')
        (ENGINE/('pending_'+uuid.uuid4().hex[:12]+'.json')).write_text(json.dumps({'request':data,'attempt':attempt+1,'variants':results,'issues':last_issues},ensure_ascii=False,indent=2),encoding='utf-8')
        if not last_issues and len(results)==2:
            on_stage('Проверяем смысл, грамматику и связность двух текстов...')
            review=complete([
                {'role':'system','content':'Ты редактор русских песенных текстов. Проверь явную бессмыслицу, ошибки падежей и согласования, несуществующие слова, уход от темы и грубые нарушения рифм. Примеры ошибок: «под крылом руля», «жизненный жизненный прыжок», «я их не бойся», рифма «минус — стремлюсь». Не придирайся к допустимым поэтическим образам. Не переписывай тексты. Верни только JSON {"passed":true,"issues":[]} или {"passed":false,"issues":["конкретная строка и ошибка"]}.'},
                {'role':'user','content':json.dumps({'topic':data['topic'],'variants':[{'title':r['title'],'lyrics':r['lyrics']} for r in results]},ensure_ascii=False)}
            ],max_tokens=1400,temperature=.15,thinking=False)
            for item in results:item['quality']['editor_review']=review
            if review.get('passed') is not True:
                remarks=review.get('issues',[])
                last_issues.extend(str(x)[:300] for x in remarks[:6])
                if not remarks:last_issues.append('Редактор не подтвердил связность; перепиши сомнительные строки.')
        log=ENGINE/('draft_'+uuid.uuid4().hex[:12]+'.json')
        log.write_text(json.dumps({'request':data,'attempt':attempt+1,'variants':results,'issues':last_issues},ensure_ascii=False,indent=2),encoding='utf-8')
        if not last_issues:return results
        messages.extend([{'role':'assistant','content':json.dumps(answer,ensure_ascii=False)},
            {'role':'user','content':'Исправь оба текста. Сохрани тему, смысл и нормальный русский язык. Замечания: '+'; '.join(last_issues)+'. Верни оба исправленных варианта в прежнем JSON.'}])
    raise RuntimeError('Новая пара не прошла проверку: '+'; '.join(last_issues[:3])+'. Предыдущий выбранный текст сохранён.')

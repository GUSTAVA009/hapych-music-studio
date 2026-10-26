"""Compact two-draft author using the existing local model. No retraining implied.
Generate unique stanzas once; repeat the chorus in code. One bounded line-edit pass.
"""
from __future__ import annotations
import json,re,time,uuid,copy
from difflib import SequenceMatcher
from lyric_writer16 import ensure_writer,session,URL,ENGINE,detect_language,validate_draft,rhyme_hint,syllables

SYSTEM='''Ты автор песен и литературный редактор. Напиши два разных оригинальных текста на языке ТЕМЫ. Тема определяет сюжет; стиль определяет звучание, а не другую тему. В каждом тексте один ясный сюжет с развитием: куплет 1 показывает ситуацию, припев выражает главную мысль, куплет 2 развивает или разрешает её. Нормальная грамматика, настоящие слова, понятные образы, никаких случайных английских вставок и непрошенной грубости. Не подменяй смысл рифмой.
В каждой строфе 4 певучие строки, примерно 8–12 слогов; рифма ААББ (строки 1–2 и 3–4). Пример полноценной пары: «Мы у причала встретим май / Ладонь из рук не выпускай». Надёжные образцы рифм: свет/ответ, домой/тобой, вперёд/идёт, счета/мечта, пора/утра, весна/тишина. Это примеры созвучий, а не обязательные слова: подбирай их по теме. Одна общая последняя гласная ещё НЕ рифма: дождя/храня не подходит. Не копируй пример и не рифмуй одинаковые слова. До ответа проверь концовки всех пар. Не описывай инструментальную аранжировку в спетых строках.
Ответ строго JSON: {"variants":[{"title":"название","story":"одна фраза о сюжете","verse1":["строка1","строка2","строка3","строка4"],"chorus":["строка1","строка2","строка3","строка4"],"verse2":["строка1","строка2","строка3","строка4"]}, {второй вариант той же структуры}]}. Припев не дублируй: программа повторит его. Не добавляй рассуждения, оценки и пояснения.'''
KEYS=('verse1','chorus','verse2')
from lyric_grammar17 import grammar_issues, normalize_generated_line

def normalize_items(items):
    for item in items:
        notes=item.setdefault('grammar_fixes',[])
        for key in KEYS:
            for i,line in enumerate(item[key]):
                fixed,changes=normalize_generated_line(line)
                item[key][i]=fixed;notes.extend(changes)
    return items

def request(messages,max_tokens=1450,temperature=.62):
    started=time.monotonic()
    response=session().post(URL+'/v1/chat/completions',json={
        'model':'local-writer','messages':messages,'temperature':temperature,'top_p':.9,
        'max_tokens':max_tokens,'repeat_penalty':1.03,'reasoning_budget':0,
        'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}},timeout=(8,180))
    response.raise_for_status();r=response.json();choice=r['choices'][0]
    if choice.get('finish_reason')=='length':raise ValueError('Автор не закончил ответ. Выбранный текст сохранён; попробуй ещё раз.')
    content=(choice['message'].get('content') or '').strip()
    content=re.sub(r'^```(?:json)?\s*|\s*```$','',content)
    answer=json.loads(content)
    (ENGINE/('reply17_'+uuid.uuid4().hex[:10]+'.json')).write_text(json.dumps(answer,ensure_ascii=False,indent=2),encoding='utf-8')
    return answer,{'seconds':round(time.monotonic()-started,2),'tokens':r.get('usage',{}).get('completion_tokens')}

def clean_variant(entry):
    if not isinstance(entry,dict):raise ValueError('Автор вернул некорректную карточку текста.')
    out={'title':str(entry.get('title','')).strip()[:65],'story':str(entry.get('story','')).strip()[:250]}
    for key in KEYS:
        lines=entry.get(key,[])
        if not isinstance(lines,list) or len(lines)!=4 or any(not isinstance(s,str) for s in lines):
            raise ValueError('Автор не закончил четверостишие; неполный текст не принят.')
        out[key]=[re.sub(r'\s+',' ',s).strip() for s in lines]
    return out

def assemble(item,repeat=True):
    sequence=[('Verse 1','verse1'),('Chorus','chorus'),('Verse 2','verse2')]
    if repeat:sequence.append(('Chorus','chorus'))
    return '\n\n'.join('['+tag+']\n'+'\n'.join(item[key]) for tag,key in sequence)

def audit(item,language,topic):
    # Evaluate unique verses, not duplicated chorus; spelling is only a rhyme hint.
    report=validate_draft(assemble(item,False),language,topic)
    report['rhyme_check']='spelling_hint_not_perceptual_score'
    if any(not line for k in KEYS for line in item[k]):report['issues'].append('Пустая строка внутри строфы.')
    if language=='ru':
        for key in KEYS:
            for line in item[key]:report['issues'].extend(grammar_issues(line))
    report['passed']=not report['issues']
    return report


def repair_weak_pairs(items,brief,review,on_stage):
    targets=[];language=brief['language']
    for v,item in enumerate(items):
        for key in KEYS:
            for pair in (0,1):
                lines=item[key][pair*2:pair*2+2]
                weak=(language=='ru' and not rhyme_hint(*lines))
                weak|=any(syllables(x)>15 for x in lines) if language=='ru' else False
                if weak:targets.append({'id':str(v)+':'+key+':'+str(pair),'variant':v,'section':key,'pair':pair,'old_lines':lines,'story':item['story']})
    for warning in review.get('unresolved',[]):
        if not isinstance(warning,dict):continue
        v=warning.get('variant');key=warning.get('section');line=warning.get('line')
        if type(v) is int and v in (0,1) and key in KEYS and type(line) is int and 0<=line<4:
            pair=line//2;ident=str(v)+':'+key+':'+str(pair)
            if not any(t['id']==ident for t in targets):targets.append({'id':ident,'variant':v,'section':key,'pair':pair,'old_lines':items[v][key][pair*2:pair*2+2],'story':items[v]['story']})
    if not targets:return {'patched_pairs':0,'resolved':not review.get('unresolved')}
    if len(targets)>6:return {'patched_pairs':0,'resolved':False}
    on_stage('Дорабатываем '+str(len(targets))+' слабые пары строк, не переписывая всю песню…')
    answer,stats=request([
        {'role':'system','content':'Исправь указанные пары песенных строк. Каждая пара обязана рифмоваться и выражать связанную понятную мысль по сюжету. Короткие строки 8–12 слогов, грамматика важнее красивостей. Можно изменить ОБЕ строки пары, не трогай остальные. Не повторяй одинаковые слова в качестве рифмы, не добавляй английские слова. Не дописывай рифмующееся слово в конец готовой фразы: сочини естественную строку целиком. Например про дорогу: «Я долго шёл один домой / И встретил утро над рекой». Ответ JSON {"pairs":[{"id":"как в запросе","lines":["строка1","строка2"]}]}. Верни все запрошенные id, никаких комментариев.'},
        {'role':'user','content':json.dumps({'brief':brief,'pairs':targets},ensure_ascii=False)}],max_tokens=900,temperature=.5)
    patches=answer.get('pairs',[])
    byid={str(x.get('id')):x.get('lines') for x in patches if isinstance(x,dict)}
    for target in targets:
        lines=byid.get(target['id'])
        if not isinstance(lines,list) or len(lines)!=2 or any(not isinstance(x,str) or not x.strip() for x in lines):return {'patched_pairs':0,'resolved':False}
        if language=='ru' and not rhyme_hint(*lines):return {'patched_pairs':0,'resolved':False}
    for t in targets:items[t['variant']][t['section']][2*t['pair']:2*t['pair']+2]=[x.strip() for x in byid[t['id']]]
    return {'patched_pairs':len(targets),'resolved':True,'timing':stats}

def create_pair(data,on_stage):
    ensure_writer();start=time.monotonic();language=detect_language(data['topic'],detect_language(data['style']))
    brief={'topic':data['topic'],'style':data['style'],'language':language}
    on_stage('Пишем две истории и рифмованные припевы…')
    answer,timing=request([{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(brief,ensure_ascii=False)}])
    entries=answer.get('variants',[])
    if len(entries)!=2:raise ValueError('Автор не вернул ровно два варианта. Старый текст сохранён.')
    items=normalize_items([clean_variant(e) for e in entries]);initial=[audit(i,language,data['topic']) for i in items]
    # Small editor output rather than rewriting both complete songs.
    on_stage('Проверяем смысл и рифмы; исправляем только слабые строки…')
    review,editor_timing=request([
        {'role':'system','content':'''Ты редактор песен. Проверь два текста: ясный связный сюжет, грамматика, естественная парная рифма ААББ и близкая длина строк. Исправь только плохие строки. Даже при удачной рифме нельзя оставлять бессмыслицу. Никакой новой темы. Не меняй хорошие строфы. Верни строго JSON {"edits":[{"variant":0,"section":"verse1","line":0,"text":"исправленная строка"}],"unresolved":[]}. Индексы variant и line начинаются с нуля. section только verse1, chorus, verse2. При исправлении рифмы можно изменить обе строки пары. Максимум 12 правок суммарно; если плохих строк больше, укажи проблему в unresolved. Если всё хорошо, edits=[] и unresolved=[]. Никаких похвал и рассуждений.'''},
        {'role':'user','content':json.dumps({'brief':brief,'variants':items,'technical_hints':initial},ensure_ascii=False)}],max_tokens=1000,temperature=.25)
    changes=review.get('edits',[])
    if not isinstance(changes,list) or len(changes)>12:raise ValueError('Редактор не завершил проверку. Выбранный текст не изменён.')
    variant_values=[str(e.get('variant')) for e in changes if isinstance(e,dict)]
    line_values=[str(e.get('line')) for e in changes if isinstance(e,dict)]
    variant_offset=1 if '2' in variant_values and '0' not in variant_values else 0
    line_offset=1 if '4' in line_values and '0' not in line_values else 0
    for edit in changes:
        if not isinstance(edit,dict):raise ValueError('Некорректная запись редактора.')
        try:
            v=int(edit.get('variant'))-variant_offset
            line=int(edit.get('line'))-line_offset
        except (ValueError,TypeError):raise ValueError('Редактор не указал номер строки.')
        key=re.sub(r'[^a-z0-9]','',str(edit.get('section','')).lower())
        value=edit.get('text')
        if v not in (0,1) or key not in KEYS or not 0<=line<4 or not isinstance(value,str):
            raise ValueError('Некорректная правка редактора; текст не заменён.')
        edit['variant']=v
        items[v][key][line]=re.sub(r'\s+',' ',value).strip()
    normalize_items(items)
    repaired=repair_weak_pairs(items,brief,review,on_stage)
    normalize_items(items)
    if repaired["resolved"]:review["unresolved"]=[]
    results=[];errors=[]
    if not repaired['resolved']:errors.append('Не удалось надёжно исправить слабые пары строк; черновик не принят.')
    for index,item in enumerate(items):
        report=audit(item,language,data['topic']);report['editor_review']={'edits':sum(e['variant']==index for e in changes),'unresolved':review.get('unresolved',[])}
        if not report['passed']:errors+=['Вариант %d: %s'%(index+1,x) for x in report['issues']]
        results.append({'id':uuid.uuid4().hex,'title':item['title'] or 'Вариант '+str(index+1),'lyrics':assemble(item),
                        'topic':data['topic'],'style':data['style'],'vocal_language':language,'vocal_gender':'auto',
                        'quality':report,'grammar_fixes':item.get('grammar_fixes',[]),'story':item['story'],'writer':'Local author / compact editing 1.7','status':'editable_draft'})
    if review.get('unresolved'):errors+=[str(x)[:180] for x in review['unresolved'][:3]]
    if SequenceMatcher(None,results[0]['lyrics'],results[1]['lyrics']).ratio()>.86:errors.append('Два варианта слишком похожи.')
    log={'request':data,'variants':results,'issues':errors,'draft_timing':timing,'editor_timing':editor_timing,'seconds':round(time.monotonic()-start,2),'pair_repair':repaired,'version':'1.7'}
    (ENGINE/('audit17_'+uuid.uuid4().hex[:12]+'.json')).write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors:raise RuntimeError('Пара не прошла проверку: '+'; '.join(errors[:2])+'. Твой выбранный текст сохранён.')
    return results

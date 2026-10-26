"""Section-local performance directions. Never turn stage directions into sung lines.
Native descriptor tags are model guidance, not a guarantee of acoustic execution.
Each repeated section keeps its own ID and directives; no cross-section merge.
"""
from __future__ import annotations
import re
from studio_text_v4 import clean_markup, split_header, prepare_request as prepare_v4

CUES = [
    (r'melodic\s+singing|напевно|связное\s+пение', 'melodic singing'),
    (r'melodic\s+rap|мелодичн\w*\s+(?:рэп|читка)', 'melodic rap'),
    (r'immediate\s+vocal\s+hook|сразу\s+припев', 'immediate vocal hook'),
    (r'full\s+bass|полн\w*\s+бас', 'full bass'),
    (r'808', '808 bass'),
    (r'intimate|интимн|доверительн', 'intimate'),
    (r'stronger|усилени', 'energetic'),
    (r'нежн|мягк|gentle|\bsoft\b|tender', 'soft'),
    (r'женск\w*\s+(?:голос|вокал)|\bfemale\b|feminine', 'female vocal'),
    (r'мужск\w*\s+(?:голос|вокал)|\bmale\b|masculine', 'male vocal'),
    (r'шум\s+моря|прибой|ocean\s*(?:waves|surf)?|sea\s+(?:waves|surf|ambience)', 'sea surf'),
    (r'ш[её]пот|whisper', 'whispered'),
    (r'игрив|улыбк|playful', 'playful'),
    (r'нараста|подъ[её]м|\bbuild', 'building energy'),
    (r'энергич|мощн|полный бит|ярк|energetic|powerful', 'energetic'),
    (r'(?:four|4)\s+low\s+male\s+(?:backing|background)\s+(?:voices?|vocals?|harmon(?:y|ies))', '4 low male backing harmonies'),
    (r'(?:four|4)\s+(?:layered\s+)?male\s+(?:backing|background)?\s*(?:voices?|vocals?|harmon(?:y|ies))|четыр[её]х?.*мужск.*бэк', '4 male backing vocals'),
    (r'бэк|harmon|backing\s+vocal', 'harmonies'),
    (r'затухан|fade', 'fade out'),
    (r'фортепиано|пианино|\bpiano', 'piano'),
    (r'\blow\s+strings\b|\bstrings\b|струнн|виолончел', 'strings'),
    (r'\bdark\s+cinematic\b|кинематограф', 'cinematic'),
    (r'\bsax(?:ophone)?\b|саксофон', 'saxophone'),
    (r'\bbaritone\b|баритон', 'baritone'),
    (r'\braspy\b|хрипл', 'raspy vocal'),
    (r'гитар|guitar', 'guitar'),
    (r'дожд|\brain\b', 'rain ambience'),
    (r'гром|thunder', 'thunder'),
    (r'аплодисмент|applause', 'applause'),
    (r'смех|laughter', 'laughter'),
    (r'разговор|spoken', 'spoken word'),
]

def compile_sections(value: str) -> dict:
    text=clean_markup(value)
    sections=[];current=None
    def begin(tag):
        nonlocal current
        current={'id':'section_%02d'%(len(sections)+1),'section':tag,'index':len(sections),
                 'scope':'this_section_only','instructions':[],'lines':[]}
        sections.append(current)
    def add_instruction(instruction,line_number):
        nonlocal current
        if current is None:begin('Intro')
        if instruction.strip():current['instructions'].append({'text':instruction.strip(),'line':line_number})
    for line_number,line in enumerate(text.splitlines(),1):
        line=re.sub(r'^\s*#{1,6}\s+','',line).strip()
        if not line or re.fullmatch(r'[\\*`_\s]*',line):
            if current and current['lines'] and current['lines'][-1]!='':current['lines'].append('')
            continue
        if line.startswith('[') and ']' not in line:
            add_instruction(line.lstrip('['),line_number);continue
        matches=list(re.finditer(r'\[([^\[\]]*)\]',line))
        if matches:
            cursor=0
            for match in matches:
                before=line[cursor:match.start()].strip()
                if before:
                    if current is None:begin('Verse 1')
                    current['lines'].append(before)
                tag,instruction=split_header(match.group(1))
                if tag:begin(tag)
                add_instruction(instruction,line_number)
                cursor=match.end()
            rest=line[cursor:].strip()
            if rest:
                if current is None:begin('Verse 1')
                current['lines'].append(rest)
            continue
        tag,instruction=split_header(line)
        if tag and (not instruction or re.search(r'[—–:]|\s-\s',line)):
            begin(tag);add_instruction(instruction,line_number);continue
        if current is None:begin('Verse 1')
        current['lines'].append(line)
    directed=[];plain=[];directions=[];warnings=[]
    for s in sections:
        # Separate sound post-production cues from musical/vocal direction tags.
        # Sending Foley words to ACE-Step risks spoken stage directions.
        def is_post_fx(value):
            return bool(re.match(r'^\s*(?:SFX|FX)\b',value,re.I) or
                        re.search(r'\b(?:SFX|FX)\s*$',value,re.I))
        raw='; '.join(x['text'] for x in s['instructions'] if not is_post_fx(x['text']))
        cues=[]
        for pattern,cue in CUES:
            if re.search(pattern,raw,re.I) and cue not in cues:cues.append(cue)
        # Combine soft + female vocal rather than sending Russian prose to sing.
        if 'soft' in cues and ('female vocal' in cues or 'male vocal' in cues):
            gender='female vocal' if 'female vocal' in cues else 'male vocal'
            cues.remove('soft');cues[cues.index(gender)]='soft '+gender
        s['cues']=cues
        s['effects']=[x for x in cues if x in ('sea surf','rain ambience','thunder','applause','laughter')]
        # Keep all original instructions visible even if a term has no safe mapping.
        if raw and not cues and not re.search(r'tape\s+click|vinyl\s+crackle|heavy\s+bass\s+drop',raw,re.I):
            warnings.append(s['id']+': нестандартное указание сохранено в плане; нет готового тега для '+raw)
        if len(', '.join(cues))>120:
            warnings.append(s['id']+': много указаний в одном разделе; точность исполнения нужно проверить на слух.')
        s['model_tag']='['+s['section']+(' - '+', '.join(cues) if cues else '')+']'
        s['lyrics']='\n'.join(s.pop('lines')).strip()
        directed.append(s['model_tag']+('\n'+s['lyrics'] if s['lyrics'] else ''))
        plain.append('['+s['section']+']'+('\n'+s['lyrics'] if s['lyrics'] else ''))
        for item in s['instructions']:
            directions.append({'section':s['section'],'section_id':s['id'],'occurrence':s['index']+1,
                               'text':item['text'],'line':item['line'],'unparsed':not bool(cues),'scope':'this_section_only'})
    model_lyrics='\n\n'.join(directed)
    if len(model_lyrics)>4096:
        compact='\n\n'.join(plain)
        if len(compact)>4096:
            raise ValueError('Вокальный текст длиннее 4096 символов после удаления SFX и описаний. ACE-Step требует разделить песню на части; слова не обрезаны.')
        model_lyrics=compact
        warnings.append('Длинные указания к вокалу сохранены отдельно; в ACE-Step отправлены короткие теги разделов без потери слов песни. SFX сводятся после генерации.')
    return {'sections':sections,'lyrics':model_lyrics,'plain_lyrics':'\n\n'.join(plain),'directions':directions,'warnings':warnings}

def prepare_request(data):
    from lyric_writer16 import detect_language
    if isinstance(data,dict):
        data=dict(data,vocal_language=detect_language(str(data.get('lyrics','')),detect_language(str(data.get('style','')))),vocal_gender='auto')
    if not isinstance(data,dict):raise ValueError('Нужен объект параметров песни.')
    if data.get('instrumental'):
        result=prepare_v4(data);result.update(sections=[],plain_lyrics=result['lyrics'],version='1.6');return result
    compiled=compile_sections(str(data.get('lyrics','')))
    # Caption describes global style only. Local directives stay on their own occurrence.
    base=dict(data,lyrics=compiled['plain_lyrics'])
    result=prepare_v4(base)
    result.update(lyrics=compiled['lyrics'],plain_lyrics=compiled['plain_lyrics'],
                  sections=compiled['sections'],directions=compiled['directions'],raw_lyrics=str(data.get('lyrics','')),
                  lyrics_length=len(compiled['lyrics']),changed_lyrics=compiled['lyrics']!=str(data.get('lyrics','')).strip(),version='1.6')
    result['warnings'].extend(compiled['warnings'])
    if compiled['directions']:
        result['warnings'].append('Музыкальные и вокальные указания остаются в тегах разделов; SFX исключены из текста для пения и передаются отдельному звуковому модулю. Точность синхронизации проверяй по готовому треку.')
    from sound_effects29 import planned_effects
    from sound_reference18 import needs_808
    result['effects_plan'] = planned_effects(compiled['sections'])
    result['sample_reference_requested'] = needs_808(str(data.get('style','')))
    if result['effects_plan']:
        result['warnings'].append('SFX сводятся отдельной стереодорожкой из локальной библиотеки: явные метки времени точные, остальные позиции приблизительные по структуре разделов. Отсутствующие записи отображаются в отчёте.')
    if result['sample_reference_requested']:
        result['warnings'].append('Для 808 используется локальный сэмпловый звуковой ориентир. Это не гарантирует точного воспроизведения басовой партии моделью.')
    result['version']='1.8'
    return result

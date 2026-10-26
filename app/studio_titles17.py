"""Fast title selection; explicit user titles are never rewritten or trimmed."""
import re,hashlib

def sung_lines(text):
    from studio_text_v4 import clean_markup
    result=[]
    for line in clean_markup(str(text)).splitlines():
        line=re.sub(r"\[[^\]\n]*\]", "", line)
        line=re.sub(r"\s+", " ", line).strip(" *`_\\")
        if line: result.append(line)
    return result

def lyric_key(text):
    return hashlib.sha256('\n'.join(sung_lines(text)).encode('utf-8')).hexdigest()

def resolve_title(data,known_variants=()):
    raw=str(data.get('title') or '')
    if raw.strip():
        if len(raw)>200:raise ValueError('Название длиннее 200 символов. Сократи его вручную: введённое название не обрезается.')
        return raw,'user'
    from studio_text_v4 import clean_markup
    lyrics=clean_markup(str(data.get('lyrics') or ''))
    key=lyric_key(lyrics)
    for variant in known_variants:
        if key==lyric_key(variant.get('lyrics','')) and variant.get('title'):
            return str(variant['title'])[:65],'selected_lyrics'
    # Derive a concise hook from the chorus without another language-model call.
    sections=re.split(r'(?m)^\s*\[([^\]]+)\]\s*',lyrics)
    preferred=[]
    for i in range(1,len(sections)-1,2):
        if re.search(r'chorus|припев',sections[i],re.I):preferred+=sung_lines(sections[i+1])
    candidates=preferred+sung_lines(lyrics)
    for line in candidates:
        phrase=re.split(r'[.!?…;:]',line)[0].strip(' ,—–-«»\"')
        words=phrase.split()
        if 2<=len(words)<=7 and 5<=len(phrase)<=65:
            return phrase[:1].upper()+phrase[1:],'chorus_hook' if line in preferred else 'lyric_hook'
    if candidates:
        words=candidates[0].strip(' ,—–-«»\"').split()[:5]
        result=' '.join(words).strip(' ,—–-«»\"')[:65]
        if result:return result[:1].upper()+result[1:],'lyric_hook'
    topic=str(data.get('topic') or '').strip()
    if topic:return ' '.join(topic.split()[:6])[:65],'topic'
    return 'Без слов' if data.get('instrumental') else 'Новая история','automatic'

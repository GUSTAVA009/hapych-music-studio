"""Music Studio: interpret a natural-language music brief without imposing a genre.
Pure prompt compilation (not a new trained model). Keeps user instructions auditable.
"""
from __future__ import annotations
import re

MAX=512
GENRES=[
 ("tropical house",r'tropical[\s-]*house|тропикал[\s-]*хаус|тропическ\w*\s+хаус','house'),
 ("deep house",r'deep[\s-]*house|дип[\s-]*хаус','house'),
 ("tech house",r'tech[\s-]*house|тех[\s-]*хаус','house'),
 ("progressive house",r'progressive[\s-]*house|прогрессив\w*\s+хаус','house'),
 ("house",r'(?<!\w)house(?!\w)|(?<!\w)хаус(?!\w)','house'),
 ("drum and bass",r'drum\s*(?:and|&|n)\s*bass|(?<!\w)dnb(?!\w)|драм[\s-]*(?:энд[\s-]*)?бейс|драм[\s-]*н[\s-]*бейс','dnb'),
 ("dubstep",r'dubstep|дабстеп','dubstep'),
 ("trance",r'\btrance\b|транс[\s-]*(?:музыка|жанр|бит)','trance'),
 ("techno",r'\btechno\b|(?<!\w)техно(?!\w)','techno'),
 ("synthwave",r'synthwave|синтвейв|ретровейв','synthwave'),
 ("drill",r'(?<!\w)drill(?!\w)|(?<!\w)дрилл(?!\w)','drill'),
 ("trap",r'(?<!\w)trap(?!\w)|(?<!\w)трэп(?!\w)|(?<!\w)треп(?!\w)','trap'),
 ("hip-hop",r'hip[\s-]?hop|хип[\s-]?хоп|(?<!\w)рэп(?!\w)|(?<!\w)rap(?!\w)','hiphop'),
 ("dancehall",r'dancehall|дансхолл|дэнсхолл|рагга','dancehall'),
 ("reggaeton",r'reggaeton|реггетон|дэмбоу|dembow','reggaeton'),
 ("reggae",r'\breggae\b|регги','reggae'),
 ("afrobeats",r'afrobeats?|афробит','afrobeats'),
 ("nu-disco",r'nu[\s-]?disco|ню[\s-]?диско','disco'),
 ("disco",r'(?<!\w)disco(?!\w)|диско','disco'),
 ("funk",r'(?<!\w)funk(?!\w)|(?<!\w)фанк(?!\w)','funk'),
 ("r&b",r'\br\s*&\s*b\b|\brnb\b|ритм[\s-]*(?:энд[\s-]*)?блюз','rnb'),
 ("soul",r'(?<!\w)soul(?!\w)|соул','soul'),
 ("indie folk",r'indie[\s-]*folk|инди[\s-]*фолк','folk'),
 ("acoustic folk",r'(?<!\w)folk(?!\w)|(?<!\w)фолк(?!\w)|акустическ\w*\s+баллад','folk'),
 ("metal",r'\bmetal\b|(?<!\w)метал(?!\w)|хэви[\s-]*металл','metal'),
 ("punk rock",r'punk[\s-]*rock|панк[\s-]*рок','rock'),
 ("pop rock",r'pop[\s-]*rock|поп[\s-]*рок','rock'),
 ("rock",r'(?<!\w)rock(?!\w)|(?<!\w)рок(?!\w)','rock'),
 ("lo-fi",r'lo[\s-]?fi|ло[\s-]?фай|лоу[\s-]?фай','lofi'),
 ("jazz",r'(?<!\w)jazz(?!\w)|(?<!\w)джаз(?!\w)|свинг|swing','jazz'),
 ("blues",r'(?<!\w)blues(?!\w)|(?<!\w)блюз(?!\w)','blues'),
 ("cinematic orchestral",r'cinematic|orchestral|симфоническ|оркестр|саундтрек|кинематографическ','orchestral'),
 ("classical",r'classical|классическ\w*\s+музык|академическ\w*\s+музык','classical'),
 ("ambient",r'(?<!\w)ambient(?!\w)|эмбиент|атмосферн\w*\s+эмбиент','ambient'),
 ("synthpop",r'synth[\s-]?pop|синти[\s-]?поп','pop'),
 ("dance pop",r'dance[\s-]?pop|танцевальн\w*\s+поп|клубн\w*\s+поп','pop'),
 ("indie pop",r'indie[\s-]?pop|инди[\s-]?поп','pop'),
 ("pop",r'(?<!\w)pop(?!\w)|(?<!\w)поп(?!\w)|поп[\s-]?музык','pop'),
 ("electronic",r'\belectronic\b|электронн\w*\s+музык|электроника','electronic'),
]
INSTRUMENTS=[
 ("808 bass",r'(?<!\d)808(?!\d)|sliding\s+(?:sub[\s-]?)?bass|скользящ\w*\s+808|слайд\w*\s+бас'),
 ("synth bass",r'synth[\s-]*bass|синтезаторн\w*\s+бас'),
 ("sub bass",r'sub[\s-]*bass|саб[\s-]*бас|глубок\w*\s+низкочастотн\w*\s+бас'),
 ("bass guitar",r'bass guitar|бас[\s-]*гитар'),
 ("acoustic guitar",r'acoustic guitar|акустическ\w*\s+гитар|испанск\w*\s+гитар'),
 ("distorted electric guitar",r'distorted(?: electric)? guitar(?: riffs?)?|electric guitar(?: riffs?)?|guitar riffs?|электрогитар|гитарн\w*\s+рифф|гитар\w*\s+с\s+перегруз'),
 ("piano",r'(?<!\w)piano(?!\w)|(?<!\w)пианино(?!\w)|фортепиано|рояль'),
 ("strings",r'(?<!\w)strings(?!\w)|струнн\w*\s+(?:секц|оркестр)|скрипк|виолончел'),
 ("brass",r'(?<!\w)brass(?!\w)|валторн|тромбон|трубы\s+оркестр'),
 ("saxophone",r'saxophone|саксофон'),
 ("clarinet",r'clarinet|кларнет'),
 ("accordion",r'accordion|аккордеон|баян'),
 ("marimba",r'marimba|маримб'),
 ("steel drums",r'steel[\s-]*drums|стил[\s-]*драм'),
 ("synth pads",r'synth[\s-]*pad|синтезаторн\w*\s+пэд|воздушн\w*\s+синтезатор'),
 ("synth lead",r'synth[\s-]*lead|синтезаторн\w*\s+лид|арпеджиатор'),
 ("acoustic drums",r'live[\s-]*drums|живая\s+ударн\w*|барабанн\w*\s+установ'),
 ("electronic drums",r'drum machine|электронн\w*\s+барабан|электронн\w*\s+ударн'),
 ("hi-hats",r'hi[\s-]*hat|хай[\s-]*хэт'),
 ("percussion",r'(?<!\w)percussion(?!\w)|перкусси|дарбук|шейкер|конга'),
]
EXCLUSIONS=[
 ("808 bass",r'808|саб[\s-]*бас|sub[\s-]*bass'),
 ("vocals",r'vocals?|вокал|голос|пени[ея]'),
 ("male vocals",r'(?<!\w)male\s+vocals?|мужск\w*\s+(?:голос|вокал)'),
 ("female vocals",r'(?<!\w)female\s+vocals?|женск\w*\s+(?:голос|вокал)'),
 ("synthesizers",r'synthesizers?|синтезатор|синт'),
 ("electronic drums",r'electronic drums|электронн\w*\s+(?:ударн|барабан)'),
 ("drums",r'drums?|барабан|ударн'),
 ("rap",r'\brap\b|рэп|читк'),
 ("trap",r'\btrap\b|трэп|треп'),
 ("guitars",r'guitars?|гитар'),
 ("vintage textures",r'vintage|lo[\s-]?fi|ло[\s-]?фай|стар\w*\s+(?:звук|семпл|инструмент)'),
]
NEG_HEAD=r'(?:\b(?:without|no|avoid|exclude)\b|(?<!\w)(?:без|никаких|исключить|избегать)(?!\w)|не\s+(?:надо|нужно|используй|использовать))'
def detect_negative_ranges(text):
    ranges=[]
    for m in re.finditer(NEG_HEAD+r'\s+([^,;.\n]{1,85})',text,flags=re.I):
        ranges.append((m.start(),m.end(),m.group(0)))
    return ranges
def masked_positive(text):
    a=list(text)
    for start,end,_ in detect_negative_ranges(text):
        for i in range(start,end):a[i]=' '
    return ''.join(a)
def compile_brief(style,prepared):
    text=str(style or '').strip()
    positive=masked_positive(text)
    # In Russian a plain "не поп" is an exclusion, not a genre request.
    positive=re.sub(r'(?<!\w)не\s+(?:поп(?:[\s-]?музыка)?|рок|рэп|хип[\s-]?хоп|джаз|метал|трэп|техно)(?!\w)',lambda m:" "*len(m.group()),positive,flags=re.I)
    # Preserve the order of genres in the user's sentence: "pop with jazz" is
    # pop-first, while "jazz with pop" is jazz-first. Prefer longer matches
    # at identical positions (tropical house over generic house).
    matches=[]
    for idx,(label,pattern,family) in enumerate(GENRES):
        match=re.search(pattern,positive,re.I)
        if match:matches.append((match.start(),-len(match.group()),idx,label,family))
    found=[]
    selected_ranges=[]
    for start,neg_length,___,label,family in sorted(matches):
        end=start-neg_length
        if any(start>=a and end<=b for a,b in selected_ranges):
            continue
        selected_ranges.append((start,end))
        if family not in [x['family'] for x in found]:
            found.append({'genre':label,'family':family})
        if len(found)>=2:break
    instruments=[label for label,pat in INSTRUMENTS if re.search(pat,positive,re.I)]
    negatives=[]
    for start,end,raw in detect_negative_ranges(text):
        for label,pattern in EXCLUSIONS:
            if re.search(pattern,raw,re.I) and label not in negatives:
                negatives.append(label)
    # "no male" must not accidentally also exclude "vocals" in general.
    if 'male vocals' in negatives or 'female vocals' in negatives:
        negatives=[v for v in negatives if v!='vocals']
    sig=re.search(r'(?<!\d)(2/4|3/4|4/4|6/8)(?!\d)',positive)
    signature=sig[1].split('/')[0] if sig else ''
    unsupported_meter=bool(re.search(r'(?<!\d)(5|7|9)\s*/\s*(4|8)(?!\d)',positive))
    # Don't force a learned trap/808 beat on acoustic, house, jazz, rock etc.
    explicit_808=bool(re.search(r'(?<!\d)808(?!\d)',positive))
    trap_like=bool(any(g['family'] in ('trap','drill') for g in found))
    allow_808=(explicit_808 or trap_like) and not set(negatives).intersection({'808 bass','electronic drums','drums'}) and not unsupported_meter
    if signature and signature!='4':allow_808=False
    # Comma-separated genre and source terms are both preserved, but explicit
    # exclusions are prioritized before optional ambience/production adjectives.
    canonical=[g['genre'] for g in found]
    exclusions=['no '+n for n in negatives]
    items=[x.strip() for x in prepared.get('caption','').split(';') if x.strip()]
    # Preserve every explicitly requested genre and instrument before optional
    # adjectives. A short description must never be silently substituted by
    # default pop / trap descriptors.
    high=[]
    for part in canonical+exclusions+instruments:
        if part not in high:high.append(part)
    priority=[]
    for val in high:
        priority.append(val)
    # Pronunciation is a singing instruction, not an implied genre. Keep
    # explicitly requested genres, exclusions and instruments first.
    native_ru = (prepared.get("vocal_language") == "ru" and
        not prepared.get("instrumental") and "vocals" not in negatives and
        not re.search(r"american\s+accent|американск\w*\s+акцент|иностранн\w*\s+акцент", text, re.I))
    if native_ru:
        priority.append("native Russian singing pronunciation; clear Russian vowels and consonants; smooth legato sustained notes; seamless register changes; restrained natural vibrato")
    for val in items:
        if val not in priority:priority.append(val)
    cleaned=[];omitted=[];seen=set()
    for chunk in priority:
        key=chunk.lower().strip('. ,;')
        if not key or key in seen:continue
        seen.add(key)
        if len('; '.join(cleaned+[chunk])) <= MAX:
            cleaned.append(chunk)
        else:omitted.append(chunk)
    caption='; '.join(cleaned)
    if not caption:raise ValueError('Не удалось составить задание для музыкальной модели.')
    plan={
       'genres':canonical,'genre_families':[g['family'] for g in found],
       'instruments':instruments,'excluded':negatives,'meter':sig[1] if sig else 'auto',
       'reference_policy':'trained_808' if allow_808 else 'none',
       'source_description':text,'model_caption':caption,
       'omitted':omitted,'section_count':len(prepared.get('sections',[])),
       'model_is_guaranteed_to_follow':False
    }
    warnings=[]
    if omitted:
        warnings.append('Не вместилось в 512 символов (без потери исходника): '+', '.join(omitted[:5]))
    if unsupported_meter:
        warnings.append('Размер 5/4, 7/4 или 9/8 не поддерживается отдельным параметром движка; передан текстом, без навязывания 4/4.')
    if negatives and '808 bass' in negatives:plan['reference_policy']='none'
    if len(canonical)==0:
        warnings.append('Жанр явно не определён. Модель использует исходное описание без искусственной подмены жанра.')
    return {'caption':caption,'style_plan':plan,'time_signature':signature,'warnings':warnings}

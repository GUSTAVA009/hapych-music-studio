"""Respect the actual brief. Add short production hints only when space permits."""
import re
from studio_producer import prepare_lyrics
LIMIT=512
HINTS=[
 (r'рагга|регги|dancehall|ragga|восточ|oriental','Syncopated dancehall drums, round bass, darbuka accents.'),
 (r'трэп|trap|drill|дрилл','Tuned 808, punchy kick, crisp snare, controlled hi-hats.'),
 (r'рэп|rap|hip.?hop|хип.?хоп','Solid kick-snare groove, defined bass, clear drum transients.'),
 (r'club|клуб|house|танцев','Steady dance groove, tight kick and bass, distinct melodic hook.'),
 (r'рок|rock','Defined live drums, focused rhythm guitars and bass.'),
]
def add_if_fits(text, additions):
    for addition in additions:
        if addition and len(text)+len(addition)+2<=LIMIT:
            text=text.rstrip('. ') + '. ' + addition
    return text

def enhance_caption(style,bpm=0,enabled=True):
    text=str(style or '').strip()
    if len(text)>LIMIT:
        raise ValueError('Описание стиля длиннее 512 символов. Сократи его: студия больше не обрезает описание незаметно.')
    if not enabled:return text
    groove=next((h for p,h in HINTS if re.search(p,text,re.I)),'')
    return add_if_fits(text,[groove,'Clean stereo separation and deliberate section transitions.'])

def enhance_vocal_clarity(caption,enabled=True):
    if not enabled:return caption
    return add_if_fits(str(caption),['Focused chest-register lead vocal, clear Russian diction, restrained vibrato.'])

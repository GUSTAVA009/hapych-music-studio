"""Honor explicit musical keys; do not quantize or retune an entire mixed track."""
import re

def key_from_brief(style):
    text=str(style)
    if re.search(r'modulat|модуляц|смен\w*\s+тональн|atonal|атональн',text,re.I):return ''
    english=re.search(r'(?<![\w])([A-G])([#b]?)\s+(major|minor)\b',text)
    if english:return english[1]+english[2]+' '+english[3]
    russian=re.search(r'\b(до|ре|ми|фа|соль|ля|си)(?:[- ](диез|бемоль))?\s+(мажор|минор)\b',text,re.I)
    if russian:
        base={'до':'C','ре':'D','ми':'E','фа':'F','соль':'G','ля':'A','си':'B'}[russian[1].lower()]
        acc={'диез':'#','бемоль':'b'}.get((russian[2] or '').lower(),'')
        return base+acc+(' minor' if russian[3].lower()=='минор' else ' major')
    return ''

def harmonic_caption(caption,style):
    if re.search(r'atonal|атональн|dissonan|диссонан|free jazz|фри.?джаз|модуляц',str(style),re.I):return caption
    hint='Согласованные бас, аккорды и мелодия; устойчивый музыкальный грув.'
    return caption+'; '+hint if len(caption)+len(hint)+2<=512 else caption

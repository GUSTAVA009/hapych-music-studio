"""Conservative local morphology checks. Not a full semantic grammar judge.
Flag only direct adjective/noun incompatibility and accidental possessive repeats.
"""
import re
from functools import lru_cache

@lru_cache(maxsize=1)
def analyzer():
    import pymorphy3
    return pymorphy3.MorphAnalyzer()

@lru_cache(maxsize=8192)
def parses(word):return analyzer().parse(word.lower())

def same_form(adjective,noun):
    a,b=adjective.tag,noun.tag
    if a.number and b.number and a.number!=b.number:return False
    cases={'loc2':'loct','gen2':'gent','voct':'nomn'}
    if a.case and b.case and cases.get(a.case,a.case)!=cases.get(b.case,b.case):return False
    if b.number!='plur' and a.gender and b.gender and str(b.gender)!='ms-f' and a.gender!=b.gender:return False
    return True

def grammar_issues(line):
    result=[]
    matches=list(re.finditer(r'[А-Яа-яЁё]+',line))
    for left,right in zip(matches,matches[1:]):
        between=line[left.end():right.start()]
        if between.strip():continue
        aa=parses(left[0]);bb=parses(right[0])
        if not aa or not bb or aa[0].tag.POS!='ADJF' or bb[0].tag.POS!='NOUN':continue
        adjectives=[p for p in aa if p.tag.POS=='ADJF']
        nouns=[p for p in bb if p.tag.POS=='NOUN' and not {'Surn','Name','Patr'}.intersection(p.tag.grammemes)]
        if not nouns:continue
        if not any(same_form(a,b) for a in adjectives for b in nouns):
            example=None
            for b in nouns:
                attrs={x for x in (b.tag.case,b.tag.number,b.tag.gender if b.tag.number!='plur' else None) if x and str(x)!='ms-f'}
                fixed=adjectives[0].inflect(attrs)
                if fixed:example=fixed.word+' '+right[0];break
            result.append('Проверь согласование «'+left[0]+' '+right[0]+'»'+('; возможная форма: «'+example+'»' if example else ''))
    duplicate=re.search(r'\b(наш|мой|твой|ваш|наша|наше|наши|моя|моё|мои)\b(?:\s+[А-Яа-яЁё]+){0,2}\s+\1\b',line,re.I)
    if duplicate:result.append('Лишний повтор: «'+duplicate[0]+'».')
    return result


def normalize_generated_line(line):
    """Fix only unambiguous local agreement in model drafts, never user's editor text."""
    matches=list(re.finditer(r'[А-Яа-яЁё]+',line));edits=[];notes=[]
    for left,right in zip(matches,matches[1:]):
        if line[left.end():right.start()].strip():continue
        aa=parses(left[0]);bb=parses(right[0])
        if not aa or not bb or aa[0].tag.POS!='ADJF' or bb[0].tag.POS!='NOUN':continue
        adjectives=[p for p in aa if p.tag.POS=='ADJF']
        nouns=[p for p in bb if p.tag.POS=='NOUN' and not {'Surn','Name','Patr'}.intersection(p.tag.grammemes)]
        if not nouns or any(same_form(a,b) for a in adjectives for b in nouns):continue
        candidates=set()
        for b in nouns:
            attrs={x for x in (b.tag.case,b.tag.number,b.tag.gender if b.tag.number!='plur' else None) if x and str(x)!='ms-f'}
            fixed=adjectives[0].inflect(attrs)
            if fixed:candidates.add(fixed.word)
        if len(candidates)==1:
            value=candidates.pop()
            if left[0][0].isupper():value=value.capitalize()
            edits.append((left.start(),left.end(),value));notes.append(left[0]+' → '+value)
    for a,b,value in reversed(edits):line=line[:a]+value+line[b:]
    pattern=r'\b(наш|мой|твой|ваш|наша|наше|наши|моя|моё|мои)\b((?:\s+[А-Яа-яЁё]+){0,2})\s+\1\b'
    def repeated(m):
        notes.append('Удалён повтор '+m[1]);return m[1]+m[2]
    line=re.sub(pattern,repeated,line,flags=re.I)
    return line,notes

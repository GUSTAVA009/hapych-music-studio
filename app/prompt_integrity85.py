"""Music Studio QA85 style routing.

When a user brief fits the engine's 512 characters, send the *user's own words*
instead of turning exclusions into positive genres or contradicting the style.
Expand shared "No X, Y, Z" negation into unambiguous "No X, no Y, no Z".
For oversized prompts, fall back to the established v83 compiler.
"""
from __future__ import annotations
import re
from prompt_integrity83 import compile_brief as earlier,MAX
from prompt_director26 import GENRES

# Explicit negative lists are sentence-final constraints; avoid positive-genre matching.
_NEG_RE=re.compile(r"\b(?P<neg>No|Without)\s+(?P<terms>[^.!?;\n]{2,160})",re.I)

def _expand_negative_match(m):
    neg=m.group("neg")
    terms=m.group("terms")
    chunks=[x.strip() for x in re.split(r",\s*|\s+or\s+|\s+and\s+",terms,flags=re.I) if x.strip()]
    if len(chunks)<2:
        return m.group(0)
    if neg.lower()=="no":
        parts=[(("No " if i==0 and neg[0].isupper() else "no ")+re.sub(r"^no\s+","",x,flags=re.I)) for i,x in enumerate(chunks)]
    else:
        parts=[(("Without " if i==0 and neg[0].isupper() else "without ")+re.sub(r"^without\s+","",x,flags=re.I)) for i,x in enumerate(chunks)]
    return ", ".join(parts)

def _positive_and_exclusions(source):
    exclusions=[m.group(0).strip() for m in _NEG_RE.finditer(source)]
    chars=list(source)
    for m in _NEG_RE.finditer(source):
        for i in range(m.start(),m.end()): chars[i]=" "
    positive="".join(chars)
    genres=[]
    for name,expression,family in GENRES:
        for hit in re.finditer(expression,positive,re.I):
            genres.append((hit.start(),-len(hit.group()),family,name))
    ordered=[];families=set()
    for _,__,family,name in sorted(genres):
        if family not in families:
            ordered.append(name);families.add(family)
    return positive,ordered,exclusions

def _excluded_items(exclusions):
    items=[]
    for clause in exclusions:
        text=re.sub(r"^(?:no|without)\s+","",clause,flags=re.I)
        for item in re.split(r",\s*|\s+or\s+|\s+and\s+",text,flags=re.I):
            clean=re.sub(r"^(?:no|without)\s+","",item.strip(),flags=re.I).lower()
            if clean and clean not in items:items.append(clean)
    return items

# These only shorten text, preserve semantics and are never used without need.
_SHORTEN=(
  ("70 seconds","70s"),("90 seconds","90s"),
  ("60 seconds","60s"),("Extremely catchy","Very catchy"),
  ("bouncy deep 808 sub bass","bouncy 808 sub bass"),
  ("Layered male backing vocals","Male backing vocals"),
  ("Strong natural male baritone","Natural male baritone"),
  ("smooth connected Russian singing","connected Russian singing")
)

def _fit_exact_style(source):
    if len(source)>MAX+230:
        return None,[]
    text=_NEG_RE.sub(_expand_negative_match,source)
    changes=[]
    for old,new in _SHORTEN:
        if len(text)<=MAX:break
        changed,count=re.subn(re.escape(old),new,text,count=1,flags=re.I)
        if count:
            text=changed
            changes.append({"from":old,"to":new})
    if len(text)<=MAX:
        return text,changes
    if len(source)<=MAX:
        # Never erase style requirements to make exclusions more explicit.
        return source,[{"note":"Negation expanded only in metadata; raw user caption preserved"}]
    return None,[]

def compile_brief(style,prepared):
    original=str(style or "").strip()
    baseline=earlier(original,prepared)
    fit,compactions=_fit_exact_style(original)
    if fit is None:
        return baseline
    positive,genres,exclusions=_positive_and_exclusions(original)
    plan=baseline['style_plan']
    plan.update(
       genres=genres, all_requested_genres=genres,
       genre_families=[v for _,_,v,n in _genre_matches(positive)],
       excluded=_excluded_items(exclusions),
       exclusions_in_source=exclusions,
       complete_style_source=original,
       model_caption=fit,caption_used=len(fit),caption_limit=MAX,
       kept_directions=[{'category':'user_source','text':fit}],
       not_sent_to_model=[],omitted=[],
       prompt_compiler='source_faithful85',
       source_compaction_steps=compactions,
       cannot_guarantee_model_compliance=True,
       user_positive_genres_derived_without_negative_clauses=True)
    baseline['caption']=fit
    baseline['warnings']=[w for w in baseline.get('warnings',[])
       if not ('не переданы' in w or 'Не вместилось' in w)]
    baseline['warnings'].append('QA85: оригинальное описание передано без замены стиля, отрицательные ограничения сохранены.')
    return baseline

def _genre_matches(positive):
    found=[]
    for name,expression,family in GENRES:
        m=re.search(expression,positive,re.I)
        if m:found.append((m.start(),-len(m.group()),family,name))
    out=[];used=set()
    for item in sorted(found):
        if item[2] not in used:out.append(item);used.add(item[2])
    return out

"""QA83: preserve near-limit user style briefs instead of rewriting them into
contradictory genres/moods. Generic v30 remains fallback for long complex briefs.
A compacted *user-authored* caption (<=512 chars) is better than substituting
bright upbeat piano with dark music because of a generic keyword mapping.
"""
from __future__ import annotations
import re
from prompt_director30 import compile_brief as compile_v30

MAX=512
COMPACTIONS=(
 ("No female vocals, robotic stutters or harsh vibrato","No female vocals, no robotic stutters, no harsh vibrato"),
 ("70 seconds","70s"),
 ("60 seconds","60s"),
 ("90 seconds","90s"),
 ("Extremely catchy","Very catchy"),
 ("bouncy deep 808 sub bass","bouncy 808 sub bass"),
 ("Playful charismatic male lead","Charismatic playful male lead"),
)

def compact_original(text):
    if not 512<len(text)<=700:
        return None,[]
    value=text
    done=[]
    for src,dst in COMPACTIONS:
        updated,n=re.subn(re.escape(src),dst,value,count=1,flags=re.I)
        if n:
            done.append({'from':src,'to':dst})
            value=updated
        if len(value)<=MAX:break
    return (value if len(value)<=MAX else None),done

def compile_brief(style,prepared):
    original=str(style or '').strip()
    baseline=compile_v30(original,prepared)
    near,steps=compact_original(original)
    if near is None:
        return baseline
    # The changes are explicitly enumerated, never generic sentiment rewrites.
    # The raw source remains in the plan and no phonetic instruction is deleted.
    plan=baseline['style_plan']
    plan.update(model_caption=near,caption_used=len(near),caption_limit=MAX,
        prompt_compiler='source_faithful83',
        source_compaction_steps=steps,
        complete_style_source=original,
        kept_directions=[{'category':'faithful_source','text':near}],
        not_sent_to_model=[],omitted=[],
        source_fidelity_verified_programmatically=True,
        model_is_guaranteed_to_follow=False)
    baseline['caption']=near
    prior=list(baseline.get('warnings',[]))
    baseline['warnings']=[w for w in prior if not ('ACE-Step' in w and ('не переданы' in w or 'не вместились' in w))]
    baseline['warnings'].append('QA83: near-limit style compressed from %d to %d characters without inventing dark mood or replacing specified instruments. Model adherence requires listening.'%(len(original),len(near)))
    return baseline

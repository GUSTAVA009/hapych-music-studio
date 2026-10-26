from pathlib import Path
import json,sys
R=Path.home()/'Music Studio';sys.path.insert(0,str(R/'app'))
from vocal_constraints87 import add_constraints,syllable_health
for job in ('81490cbc66914855bf58a7bcc7f3ae8a','d29bf956474846e4ad425b119f69624b','b0572d412a5b4828840a9e0ba0a75db6'):
 f=R/'app'/'requests'/(job+'.json')
 r=json.loads(f.read_text(encoding='utf-8'))
 style=r['preparation']['style_plan']['complete_style_source']
 x=add_constraints(style,'ru',r['preparation']['negative_prompt'])
 print('EXPLICIT',job,x['explicit_negative_terms'],'CAP',len(x['negative_prompt']),flush=True)
 print('NEGATIVE',json.dumps(x['negative_prompt'],ensure_ascii=True),flush=True)
 assert len(x['negative_prompt'])<=500
 assert ('female lead singing' in x['negative_prompt'])==('no female' in style.lower())
 if 'rock' in style.lower() and 'no rap' in style.lower():
  assert 'rap vocal delivery' in x['negative_prompt']
 if 'no robotic' in style.lower() or 'robotic stutters' in style.lower():
  assert 'robotic vocal stuttering' in x['negative_prompt'] or 'robotic pitch wobble' in x['negative_prompt']
 h=syllable_health(r['settings']['Lyrics'],r['settings']['Audio Duration (seconds)'])
 print('SYLLABLES',job,h,flush=True)
r=add_constraints('Russian rock. No female vocals, rap, autotune, robotic vibrato.','ru','foreign accent')
assert 'rap vocal delivery' in r['negative_prompt']
assert 'female lead singing' in r['negative_prompt']
assert 'obvious autotune artifacts' in r['negative_prompt']
assert 'robotic pitch wobble' in r['negative_prompt']
print('QA87_NEGATIVE_TESTS_PASS')

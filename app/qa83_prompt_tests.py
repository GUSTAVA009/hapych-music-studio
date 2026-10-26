"""QA83 compiler regression for the exact user request and unchanged dark prompt."""
import json,sys
from pathlib import Path
R=Path.home()/'Music Studio';sys.path.insert(0,str(R/'app'))
from prompt_integrity83 import compile_brief
from prompt_director30 import compile_brief as old
job='91ce163d15784ad28efdb30905563c34'
request=json.loads((R/'app'/'requests'/(job+'.json')).read_text(encoding='utf-8'))
style=request['preparation']['style_plan']['complete_style_source']
prepared={'sections':[],'vocal_language':'ru','instrumental':False}
a=old(style,prepared)
b=compile_brief(style,prepared)
print('OLD_CAPTION',json.dumps(a['caption'],ensure_ascii=True))
print('NEW_CAPTION',json.dumps(b['caption'],ensure_ascii=True))
print('NEW_META',b['style_plan']['prompt_compiler'],'CHAR',len(b['caption']),'OMITTED',b['style_plan']['omitted'])
assert len(b['caption'])<=512
assert 'bright funky piano' in b['caption'].lower()
assert 'joyful party vibe' in b['caption'].lower()
assert 'robotic stutters' in b['caption'].lower()
assert 'jersey club rhythm' in b['caption'].lower()
assert 'dark melancholic piano' not in b['caption'].lower()
assert 'cinematic development' not in b['caption'].lower()
assert 'male backing vocals' in b['caption'].lower()
assert b['style_plan']['complete_style_source']==style
for other in ['Dark noir with dark melancholic piano, tense urban atmosphere, 100 BPM.',
  'Bright funky piano, female sweet lead, playful party music, 105 BPM.']:
  result=compile_brief(other,prepared)
  print('CONTROL',json.dumps(result['caption'],ensure_ascii=True))
  assert result['style_plan']['prompt_compiler']=='loss_aware_style30'
  if 'Bright funky piano' in other:
   assert 'bright funky piano' in result['caption'].lower()
   assert 'dark melancholic' not in result['caption'].lower()
  if 'Dark noir' in other:
   assert 'dark melancholic piano' in result['caption'].lower()
assert compile_brief('x'*900,prepared)['style_plan']['prompt_compiler']=='loss_aware_style30'
print('QA83_PROMPT_TESTS_PASS')

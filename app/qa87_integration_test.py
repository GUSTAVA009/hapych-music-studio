from pathlib import Path
import sys,json,inspect
R=Path.home()/'Music Studio';sys.path.insert(0,str(R/'app'))
from studio_server import prepare_request,generate_worker
from vocal_constraints87 import add_constraints,syllable_health
for job in ('81490cbc66914855bf58a7bcc7f3ae8a','d29bf956474846e4ad425b119f69624b'):
 req=json.loads((R/'app'/'requests'/(job+'.json')).read_text(encoding='utf-8'))
 style=req['preparation']['style_plan']['complete_style_source']
 data={'style':style,'lyrics':req['preparation'].get('raw_lyrics',req['settings']['Lyrics']),'duration':req['settings']['Audio Duration (seconds)'],
  'bpm':req['settings']['BPM (Beats Per Minute)'] or 0,'two_versions':True}
 prepared=prepare_request(data)
 ref=add_constraints(style,prepared['vocal_language'],prepared['negative_prompt'])
 lex=syllable_health(prepared['lyrics'],req['settings']['Audio Duration (seconds)'])
 assert 'female lead singing' in ref['negative_prompt']
 assert 'missing Russian word endings' in ref['negative_prompt']
 assert len(prepared['caption'])<=512
 assert len(ref['negative_prompt'])<=500
 if 'rap' in style.lower() and 'no rap' in style.lower():
  assert 'rap vocal delivery' in ref['negative_prompt']
 assert prepared['style_plan']['prompt_compiler']=='source_faithful85'
 print('SERVER_PREPARED',job,'compiler',prepared['style_plan']['prompt_compiler'],'negative_terms',ref['explicit_negative_terms'],
   'vowels',lex['syllables'],'risky',lex['requires_review'],flush=True)
src=inspect.getsource(generate_worker)
assert 'from vocal_constraints87 import add_constraints, syllable_health' in src
assert 'prepared["negative_prompt"] = vocal_exclusions["negative_prompt"]' in src
assert 'settings = {' in src
print('QA87_INTEGRATION_PASS',flush=True)

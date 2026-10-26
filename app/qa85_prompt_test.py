from pathlib import Path
import json,sys
R=Path.home()/'Music Studio'
sys.path.insert(0,str(R/'app'))
from prompt_integrity85 import compile_brief
p={'vocal_language':'ru','instrumental':False,'sections':[]}
job_ids=['91ce163d15784ad28efdb30905563c34','d29bf956474846e4ad425b119f69624b']
for job in job_ids:
 path=R/'app'/'requests'/(job+'.json')
 r=json.loads(path.read_text(encoding='utf-8'))
 src=r['preparation']['style_plan']['complete_style_source']
 result=compile_brief(src,p)
 out=result['caption']
 plan=result['style_plan']
 print('JOB',job,'ORIGINAL',len(src),'SENT',len(out),
    'compiler',plan.get('prompt_compiler'),'genres',plan.get('genres'),
    'negations',plan.get('exclusions_in_source'),flush=True)
 print('CAPTION',json.dumps(out,ensure_ascii=True),flush=True)
 assert len(out)<=512
 if job.startswith('d29'):
  assert 'Modern Russian alternative rock' in out
  assert 'No female vocals' in out
  assert 'no rap' in out.lower()
  assert 'no autotune' in out.lower()
  assert 'no robotic vibrato' in out.lower()
  assert 'hip-hop' not in out.lower()
  assert 'hip-hop' not in plan['genres']
  assert 'rock' in plan['genres']
 if job.startswith('91c'):
  assert 'bright funky piano' in out.lower()
  assert 'joyful party vibe' in out.lower()
  assert 'dark melancholic piano' not in out.lower()
  assert 'no robotic stutters' in out.lower()
  assert 'male backing vocals' in out.lower()
tests=[
 'Warm melodic synth-pop; male vocals; no female vocals, no shouting; fun piano.',
 'Fast Russian rock. No rap, autotune, robotic vibrato. Guitars and drums.',
 'Funky piano dance music with natural male bass, 120 BPM.',
 'Jazz, but no rap or autotune. Warm sax.',
]
for s in tests:
 out=compile_brief(s,p)
 print('CASE',json.dumps(out['caption'],ensure_ascii=True),out['style_plan']['genres'],flush=True)
 assert len(out['caption'])<=512
 assert 'hip-hop' not in out['style_plan']['genres'] or 'no rap' not in s.lower()
assert compile_brief('x'*900,p)['style_plan']['prompt_compiler']!='source_faithful85'
print('QA85_ALL_TESTS_PASS',flush=True)

"""QA90 live routes/preflight: no music is generated."""
from pathlib import Path
import json,requests
r=Path.home()/'Music Studio'
url='http://127.0.0.1:7870'
health=requests.get(url+'/api/health',timeout=8);health.raise_for_status()
info=health.json()
assert info['ready'] and info['job']['status'] in ('idle','done','error')
for path in ('/','/qa90-style-compare'):
 t=requests.get(url+path,timeout=8)
 assert t.status_code==200,(path,t.status_code)
 print('HTTP_PAGE',path,t.status_code,len(t.content))
for n in ('forced','native'):
 response=requests.get(url+'/api/qa90-audio/'+n,
   headers={'Range':'bytes=0-1023'},timeout=10)
 assert response.status_code==206 and len(response.content)==1024,(n,response.status_code)
 print('MP3_RANGE',n,response.status_code,response.headers.get('Content-Range'))
latest=json.loads((r/'app'/'requests'/'81490cbc66914855bf58a7bcc7f3ae8a.json').read_text(encoding='utf8'))
raw=latest['preparation']['style_plan']['complete_style_source']
payload={'style':raw,'lyrics':latest['settings']['Lyrics'],'duration':70,'bpm':130,
     'use_voice':False,'use_trained_groove_reference':False}
def submit(data):
 resp=requests.post(url+'/api/prepare',json=data,timeout=12)
 if resp.status_code!=200:raise RuntimeError(f'{resp.status_code} {resp.text[:250]}')
 return resp.json()
baseline=submit(payload)
assert baseline['style_plan']['prompt_compiler']=='source_faithful85'
assert 'voice_model_preview' not in baseline
assert not baseline['groove_reference_opt_in']
guide=submit(dict(payload,use_trained_groove_reference=True))
assert guide['groove_reference_opt_in'] is True
print('QA90_PREFLIGHT_GUIDE',baseline['groove_reference_opt_in'],guide['groove_reference_opt_in'])
last=json.loads((r/'app'/'requests'/'d29bf956474846e4ad425b119f69624b.json').read_text(encoding='utf8'))
mine=submit(dict(payload,use_voice=True,voice=last['voice_routing']['selected_recording'],
        voice_profile_id=last['voice_routing']['validated_profile_id']))
assert mine['voice_model_preview']['trained'] is True,mine['voice_model_preview']
print('QA90_ASSIGNED_PROFILE',json.dumps(mine['voice_model_preview'],ensure_ascii=True))
free=json.loads((r/'app'/'requests'/'b0572d412a5b4828840a9e0ba0a75db6.json').read_text(encoding='utf8'))
base=submit(dict(payload,use_voice=True,voice=free['voice_routing']['selected_recording'],
        voice_profile_id=''))
assert base['voice_model_preview']['trained'] is False
print('QA90_UNASSIGNED_PROFILE',json.dumps(base['voice_model_preview'],ensure_ascii=True))
print('QA90_LIVE_INTEGRATION_PASS',flush=True)

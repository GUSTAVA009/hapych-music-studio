"""QA90 composer regression: default never forces melody/key, opt-in still works.

No actual generation/track writes and no changes to history.
"""
from pathlib import Path
import sys,json,requests
R=Path.home()/'Music Studio';sys.path.insert(0,str(R/'app'))
import composer90
job='81490cbc66914855bf58a7bcc7f3ae8a'
request=json.loads((R/'app'/'requests'/(job+'.json')).read_text(encoding='utf-8'))
variant=json.loads((R/'app'/'requests'/(job+'_variants.json')).read_text(encoding='utf-8'))[0]
config=requests.get('http://127.0.0.1:7862/config',timeout=12).json()
comps={x['id']:x for x in config['components']}
dep=next(d for d in config['dependencies'] if d.get('api_name')=='generation_wrapper')
outputs=[comps[i].get('props',{}).get('label') for i in dep['outputs'] if not comps[i].get('skip_api',comps[i]['type']=='state')]
fixed=R/'Diagnostics'/'QA90-NativeStyle'/'no_reference_70s.wav'
assert fixed.exists()
class Job:
 def done(self):return True
 def result(self):
  return [str(fixed) if label=='🎵 Generated Music (Sample 1)' else '' for label in outputs]
class Client:
 history=[]
 def __init__(self,*args,**kwargs):pass
 def predict(self,*args,**kwargs):return None
 def submit(self,*args,**kwargs):
  props=[comps[i].get('props',{}).get('label') for i in dep['inputs'] if comps[i]['type']!='state']
  assert len(props)==len(args)==72
  self.history.append(dict(zip(props,args)))
  return Job()
composer90.fresh_seeds=lambda style,count:[889349091+i for i in range(count)]
calls=[]
orig_make=composer90.make_reference
def fake_make(style,bpm,key,seed):
 calls.append((style,bpm,key,seed))
 return {'path':str(variant['reference']['path']),'kind':'trained_groove24_sample_reference',
  'reference_key':'D minor','bpm':130,'plan':variant['reference']['plan']}
composer90.make_reference=fake_make
base=dict(variant['settings'])
base.update({'Batch Size':1,'Random Seed':False,'Seed':'889349091',
             '__style_plan':request['preparation']['style_plan'],
             'Key':request['settings']['Key'],
             'Time Signature':request['settings'].get('Time Signature','')})
for opt in [False,True]:
 Client.history.clear();calls.clear()
 settings=dict(base,__use_trained_groove_reference=opt)
 paths,_,records=composer90.compose(settings,config,request['preparation']['style_plan']['complete_style_source'],'new','http://127.0.0.1:7862','QA90TEST',lambda s:None,client_factory=Client)
 sent=Client.history[-1];record=records[0]
 if not opt:
  assert not calls
  assert sent['Reference Audio'] is None, type(sent['Reference Audio'])
  assert sent['Key']==''
  assert sent['BPM (Beats Per Minute)']==130
  assert record['reference_source']=='none'
  assert record['automatic_minor_key_forced'] is False
 else:
  assert calls and sent['Reference Audio'] is not None
  assert sent['Key']=='D minor'
  assert record['reference_source']=='explicit_groove_opt_in'
  assert record['automatic_minor_key_forced']
 print('COMPOSER90_TEST_OK',opt,'source',record['reference_source'],
       'key',sent['Key'],'reference_audio',bool(sent['Reference Audio']),flush=True)
print('QA90_COMPOSER_REGRESSION_PASS')

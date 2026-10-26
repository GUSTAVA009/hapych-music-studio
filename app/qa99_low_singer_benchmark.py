"""QA99 register-aligned generation against the SAME seed/lyrics/BPM as QA86.

Does ACE Step obey a realistic owner-compatible Russian bass-baritone
instruction? User's personal voice is never used for this baseline test.
No new content is added to Music Studio library.
"""
from pathlib import Path
from gradio_client import Client
import requests,time,json,shutil,sys,hashlib
R=Path.home()/'Music Studio'
D=R/'Diagnostics'/'QA99-LowRegister';D.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'app'))
from qa86_sft_benchmark import LYRICS
baseurl='http://127.0.0.1:7870';url='http://127.0.0.1:7862'
state=requests.get(baseurl+'/api/status',timeout=10).json()['status']
assert state in ('idle','done','error'),state
config=requests.get(url+'/config',timeout=12).json()
comps={c['id']:c for c in config['components']}
dep=next(x for x in config['dependencies'] if x.get('api_name')=='generation_wrapper')
model=next((c['props'].get('value') for c in config['components'] if c.get('props',{}).get('label')=='Main Model Path'),'unknown')
assert 'turbo' in str(model),model
prompt=("Russian upbeat dance-pop, 120 BPM. Deep NATURAL male bass-baritone, "
 "warm chest resonance, native Russian clear smooth connected singing, "
 "comfortable low vocal register B2-E3 throughout, avoid high strained tenor "
 "notes and falsetto. Fully pronounced Russian word endings and soft legato, "
 "minimal vibrato, playful rhythmic hook. Bouncy deep 808 bass, punchy groove, "
 "bright funky piano, claps. Clean punchy polished mix, male vocals only.")
v={'Music Caption':prompt,'Lyrics':LYRICS,
 'Audio Duration (seconds)':35,'BPM (Beats Per Minute)':120,
 'Batch Size':1,'Vocal Language':'ru','Random Seed':False,'Seed':'7813095',
 'DiT Inference Steps':8,'Shift':3.0,'LM Temperature':0.75,
 'LM Batch Chunk Size':1,'LM Codes Hints':'',
 'LM Negative Prompt':'high pitched tenor, falsetto, nasally female sounding voice, off key singing, unstable melody, broken Russian consonants, word endings missing, robotic vibrato, autotune',
 'CoT Metas (Chain-of-Thought Metadata)':True,'CoT Language Detection':False,
 'Think':True,'CaptionRewrite':False,'Auto LRC':False,'Auto Score':False,
 'Audio Format':'wav','MP3 Bitrate':'320k','Reference Audio':None,'Key':'','Time Signature':''}
args=[]
for id in dep['inputs']:
 c=comps[id]
 if c['type']=='state':continue
 prop=c.get('props',{})
 args.append(v.get(prop.get('label'),prop.get('value')))
assert len(args)==72,len(args)
info={'test':'QA99','config':model,'seed':'7813095','BPM':120,
 'lyrics_unchanged':True,'prompt':prompt,'voice_reference_used':False,
 'reference_audio_used':False,'studio_tracks_modified':False,
 'voice_profile_f0_median_hz':120.8,
 'user_voice_sample_origin':'Existing QA54',
 'requested_low_singer_note_range':'B2-E3','status':'running'}
try:
 print('QA99_GENERATION_START',model,flush=True)
 cli=Client(url,verbose=False);cli.predict(False,api_name='/set_use_lora')
 t=time.monotonic();job=cli.submit(*args,api_name='/generation_wrapper')
 while not job.done():
  if time.monotonic()-t>780:
   job.cancel();raise TimeoutError('QA99 generation timed out')
  stage=requests.get(baseurl+'/api/status',timeout=7).json()['status']
  if stage in ('preparing','generating','converting'):
   job.cancel();raise RuntimeError('User started Music Studio; QA99 canceled')
  time.sleep(1)
 reply=job.result();out_ids=[x for x in dep['outputs'] if not comps[x].get('skip_api',comps[x]['type']=='state')]
 data={comps[x].get('props',{}).get('label'):val for x,val in zip(out_ids,reply)}
 wav=data.get('🎵 Generated Music (Sample 1)')
 if isinstance(wav,dict):wav=wav.get('value',wav.get('path'))
 assert isinstance(wav,str) and Path(wav).is_file(),data.keys()
 out=D/'qa99_lowbaritone_35s.wav';shutil.copy2(wav,out)
 import subprocess
 mp3=D/'qa99_lowbaritone_35s_320.mp3'
 r=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(out),
 '-c:a','libmp3lame','-b:a','320k',str(mp3)],capture_output=True,text=True,timeout=90)
 assert r.returncode==0,r.stderr
 info.update(status='generated',audio=str(out),mp3=str(mp3),
  generated_s=round(time.monotonic()-t,2),sha256=hashlib.sha256(out.read_bytes()).hexdigest())
 print('QA99_SOURCE_READY',json.dumps(info,ensure_ascii=True),flush=True)
except Exception as err:
 info.update(status='failed',error=repr(err))
 print('QA99_SOURCE_FAIL',repr(err),flush=True)
finally:
 (D/'qa99_generation_report.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf8')

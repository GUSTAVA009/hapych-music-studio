"""Render trained rhythm with licensed drum samples and tuned mono 808.
Source audio and voices never leave this computer. No weight update at runtime.
"""
from pathlib import Path
from fractions import Fraction
import subprocess,json,hashlib,os
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly,butter,sosfiltfilt
from arrangement21 import choose_plan as basic_choose_plan,catalog,select,load
from groove_preflight import ensure_available
import re
from sound_reference18 import needs_808

def rhythmic_guide(style):
    t=str(style or '')
    if re.search(r'(?:without|no|без)\s+(?:drums|percussion|барабан|ударн)',t,re.I):
        return False
    if needs_808(t):
        return True
    if re.search(r'ambient|orchestral|классическ|оркестр|piano solo|фортепиано соло|acoustic ballad|акустическ.*баллад',t,re.I):
        return False
    return bool(re.search(r'house|dance|disco|edm|dancehall|reggaeton|afrobeat|modern pop|dance pop|upbeat pop|hip[- ]?hop|hiphop|r[&n]b|synth.?pop|groov[ey]|radio pop|танцевальн|клубн|дэнс|хип.?хоп|рэп|современ.*бит|поп[- ]музык|современн.*поп',t,re.I))

def choose_plan(style,bpm=0,key='',seed=None):
    if not rhythmic_guide(style):
        return None
    # Modern pop uses the trained pop/dance rhythm class; the added 808 marker
    # is only the existing harmonic plan's opt-in gate, not the genre label.
    plan_style=style if needs_808(style) else str(style)+'; 808 low-end reference'
    return basic_choose_plan(plan_style,bpm,key,seed)

ROOT=Path.home()/'Music Studio';LIB=ROOT/'Sound Library';SR=48000
PY=ROOT/'ACE-Step-1.5'/'.venv'/'Scripts'/'python.exe'

def make_reference(style,bpm=0,key='',seed=None):
 plan=choose_plan(style,bpm,key,seed)
 if plan is None:return None
 # This is an OPTIONAL, locally trained model excluded from public ZIPs.
 # Preflight gives a meaningful error instead of a bare FileNotFoundError.
 ensure_available(ROOT)
 weight=ROOT/'Training Runs'/'groove23'/'best_groove_model.pt'
 weight_hash=hashlib.sha256(weight.read_bytes()).hexdigest()
 token=hashlib.sha256((json.dumps(plan,sort_keys=True)+str(style)+weight_hash+'production24a').encode()).hexdigest()[:20]
 folder=LIB/'references24'/token;folder.mkdir(parents=True,exist_ok=True)
 output=folder/'arrangement.wav';meta=folder/'plan.json'
 if output.is_file() and meta.is_file():return {'path':str(output),**json.loads(meta.read_text(encoding='utf-8'))}
 bars=8 if plan['bpm']>=48 else 4;beat=60/plan['bpm'];n=round(bars*4*beat*SR)
 request=folder/'request.json';rhythm_path=folder/'rhythm.json'
 request.write_text(json.dumps({'style':str(style),'bpm':plan['bpm'],'seed':plan['seed'],'bars':bars},ensure_ascii=False),encoding='utf-8')
 proc=subprocess.run([str(PY),str(Path(__file__).with_name('learned_rhythm24.py')),'--request',str(request),'--output',str(rhythm_path)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
 if proc.returncode:raise RuntimeError('Обученный ритм не создан: '+proc.stderr[-350:])
 rhythm=json.loads(rhythm_path.read_text(encoding='utf-8'))
 rng=np.random.default_rng(int(plan['seed']));rows={}
 for role,category,maximum,tuned in [('bass','bass_one_shot',8,True),('kick','kick_one_shot',1.3,False),('snare','snare_one_shot',.8,False),('hat','hat_one_shot',.45,False),('open_hat','hat_one_shot',1.2,False),('clap','clap_one_shot',.6,False)]:
  rows[role]=select(category,rng,maximum,tuned)
 sounds={k:load(row) for k,row in rows.items()}
 tracks={'drums':np.zeros((n,2),np.float32),'bass':np.zeros((n,2),np.float32)};notes=[]
 def envelope(x,attack=.002,release=.018):
  x=x.copy();a=min(len(x)//3,round(attack*SR));r=min(len(x)//3,round(release*SR))
  if a:x[:a]*=np.linspace(0,1,a)
  if r:x[-r:]*=np.linspace(1,0,r)
  return x
 def put(name,x,at,gain=1,pan=0):
  start=round(at*SR);length=min(len(x),n-start)
  if start<0 or length<=0:return
  left=np.sqrt((1-pan)/2);right=np.sqrt((1+pan)/2)
  tracks[name][start:start+length,0]+=x[:length]*gain*left
  tracks[name][start:start+length,1]+=x[:length]*gain*right
 # The learned model chooses onset/velocity/microtiming. Renderer only selects
 # timbres, avoids overlapping bass notes and controls mix headroom.
 mapping={0:('kick',.74,0,.38),1:('snare',.34,0,.28),2:('hat',.15,-.13,.12),3:('open_hat',.12,.16,.30)}
 for e in rhythm['events']:
  name,level,pan,cap=mapping[e['role']];at=e['beat']*beat;vel=(e['velocity']/100)**1.15
  put('drums',envelope(sounds[name][:round(cap*SR)]),at,level*vel,pan)
  if e['role']==1:put('drums',envelope(sounds['clap'][:12000]),at+.008,.09*vel,.05)
 kicks=[e for e in rhythm['events'] if e['role']==0];tuned={}
 for index,e in enumerate(kicks):
  bar=min(bars-1,int(e['beat']//4));pc=plan['chords'][bar%4]['root_pc'];midi=24+pc
  if midi<28:midi+=12
  hz=440*2**((midi-69)/12)
  if midi not in tuned:
   ratio=Fraction(rows['bass']['tuning']['hz']/hz).limit_denominator(2000)
   tuned[midi]=resample_poly(sounds['bass'],ratio.numerator,ratio.denominator).astype('float32')
  next_kick=kicks[index+1]['beat'] if index+1<len(kicks) else bars*4
  end=min(next_kick-.03,(bar+1)*4,bars*4,e['beat']+2.5);duration=max(.1,(end-e['beat'])*beat)
  tone=envelope(tuned[midi][:round(duration*SR)],attack=.008,release=.035)
  put('bass',tone,e['beat']*beat,.60*(e['velocity']/100),0)
  notes.append({'beat':e['beat'],'midi':midi,'hz':hz,'bar':bar})
 # Kick-triggered bass ducking, 3 dB maximum, has no effect on vocal audio.
 duck=np.ones(n,np.float32)
 for e in kicks:
  start=round(e['beat']*beat*SR);length=min(round(.12*SR),n-start)
  if length>0:duck[start:start+length]*=1-.29*np.exp(-np.arange(length)/(SR*.035))
 tracks['bass']*=duck[:,None]
 tracks['bass']=sosfiltfilt(butter(2,[24,1500],btype='bandpass',fs=SR,output='sos'),tracks['bass'],axis=0).astype('float32')
 mix=tracks['drums']+tracks['bass'];peak=float(np.max(np.abs(mix)));gain=min(1,.89/max(peak,1e-8))
 for name,x in tracks.items():sf.write(folder/(name+'.wav'),x*gain,SR,subtype='PCM_24')
 sf.write(output,mix*gain,SR,subtype='PCM_24')
 assert all(e['midi']%12 in plan['scale_pcs'] for e in notes)
 info={'kind':'trained_groove24_sample_reference','plan':plan,'reference_key':plan['key'],'bpm':plan['bpm'],'seconds':n/SR,'samples':{k:v['path'] for k,v in rows.items()},'model_sha256':weight_hash,'model_step':rhythm['model_step'],'learned_weights_used':True,'rhythm_event_count':len(rhythm['events']),'rhythm_patterns':rhythm['patterns'],'events':notes,'out_of_scale_note_events':0,'private_stems':str(folder),'sample_rate':SR,'usage':'Learned percussion rendered into Reference Audio. Final musical audio still generated by ACE-Step.','acoustic_quality_verified':False,'peak_dbfs':round(20*np.log10(max(peak*gain,1e-8)),2)}
 meta.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
 return {'path':str(output),**info}

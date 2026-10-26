"""Key-coherent sample arrangement; private composition-licensed samples, no weight updates."""
from pathlib import Path
from functools import lru_cache
from math import gcd
import hashlib,json,re,secrets
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly,butter,sosfiltfilt
from sound_reference18 import needs_808
from music_plan17 import key_from_brief
R=Path.home()/'Music Studio';LIB=R/'Sound Library';SR=48000
NOTES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
@lru_cache(maxsize=1)
def catalog():return json.loads((LIB/'catalog20.json').read_text(encoding='utf-8'))

def choose_plan(style,bpm=0,key='',seed=None):
 seed=secrets.randbelow(2147483646)+1 if seed is None else int(seed)
 text=str(style)
 if re.search(r'(?<![0-9])(?:3/4|6/8|5/4|7/8)|waltz|вальс',text,re.I):return None
 if not needs_808(text) or re.search(r'atonal|атональн|modulat|модуляц|смен\w*\s+тональн',text,re.I):return None
 rng=np.random.default_rng(int(hashlib.sha256((text+'|'+str(seed)).encode()).hexdigest()[:12],16))
 mode='major' if re.search(r'\bmajor\b|мажор',text,re.I) and not re.search(r'\bminor\b|минор',text,re.I) else 'minor'
 chosen=key or key_from_brief(text);automatic_key=not bool(chosen)
 if not chosen:chosen=str(rng.choice(['C','D','G'] if mode=='major' else ['A','D','E']))+' '+mode
 m=re.fullmatch(r'([A-G])([#b]?)\s+(major|minor)',chosen,re.I)
 if not m:raise ValueError('Неизвестная тональность: '+chosen)
 tonic=({'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[m[1].upper()]+{'':0,'#':1,'b':-1}[m[2]])%12;mode=m[3].lower()
 tempo=float(bpm or 0)
 if not tempo:
  match=re.search(r'\b(\d{2,3})\s*(?:BPM|уд/?мин)',text,re.I)
  tempo=float(match[1]) if match else (142 if re.search(r'trap|drill|трэп|дрилл',text,re.I) else 102)
 if not 30<=tempo<=300:raise ValueError('Темп должен быть 30–300 BPM.')
 scale=[0,2,3,5,7,8,10] if mode=='minor' else [0,2,4,5,7,9,11]
 progressions=([(0,5,2,6),(0,3,5,6),(0,6,5,6),(0,2,6,3),(0,5,3,6),(0,3,6,2)] if mode=='minor' else [(0,4,5,3),(0,5,1,4),(5,3,0,4),(0,3,4,0),(0,2,3,4),(3,4,2,5)])
 progression_index=int(seed)%len(progressions);degrees=progressions[progression_index];chords=[]
 for degree in degrees:
  pitches=[tonic+scale[(degree+n)%7]+12*((degree+n)//7) for n in (0,2,4)]
  quality='m' if (pitches[1]-pitches[0])%12==3 else ''
  chords.append({'name':NOTES[pitches[0]%12]+quality,'pitch_classes':[x%12 for x in pitches],'root_pc':pitches[0]%12})
 return {'key':NOTES[tonic]+' '+mode,'key_origin':'automatic_shared_plan' if automatic_key else 'user','tonic':tonic,'scale_pcs':[(tonic+n)%12 for n in scale],'bpm':tempo,'chords':chords,'seed':int(seed),'schema':21,'progression_index':progression_index,'groove_index':(int(seed)//7)%6}

def load(row):
 p=(LIB/row['path']).resolve()
 if LIB.resolve() not in p.parents:raise ValueError('Invalid catalog path')
 a,sr=sf.read(p,dtype='float32',always_2d=True);x=a[:,int(np.argmax(np.mean(a.astype(float)**2,axis=0)))];x=x-x.mean()
 if sr!=SR:
  g=gcd(sr,SR);x=resample_poly(x,SR//g,sr//g)
 peak=float(np.max(np.abs(x)))
 if peak<.001:raise ValueError('Silent sample')
 return (x/peak).astype('float32')

def select(cat,rng,maximum=None,tuned=False):
 pool=[r for r in catalog()['samples'] if r['category']==cat and r['usable'] and (maximum is None or .01<r['seconds']<maximum) and (not tuned or (r.get('tuning') and r['tuning']['cents_spread']<=8 and r['tuning']['periodicity']>=.9))]
 if cat=='hat_one_shot':
  electronic=[r for r in pool if not re.search('acousti|live|vintage',r['path'],re.I)]
  if electronic:pool=electronic
 if not pool:raise ValueError('Нет подходящих сэмплов: '+cat)
 return pool[int(rng.integers(len(pool)))]

def render_reference(style,plan):
 if plan is None:return None
 token=hashlib.sha256((json.dumps(plan,sort_keys=True)+'|'+str(style)+'|diversity21-v1').encode()).hexdigest()[:20]
 folder=LIB/'references21'/token;folder.mkdir(parents=True,exist_ok=True);out=folder/'arrangement.wav';meta=folder/'plan.json'
 if out.is_file() and meta.is_file():return {'path':str(out),**json.loads(meta.read_text(encoding='utf-8'))}
 rng=np.random.default_rng(int(token[:12],16));beat=60/plan['bpm'];bars=8 if beat<=1.25 else 4
 n=int(round(bars*4*beat*SR));tracks={name:np.zeros(n,np.float32) for name in ['bass','drums','harmony']};events=[]
 rows={'bass':select('bass_one_shot',rng,8,True),'kick':select('kick_one_shot',rng,1.3),'snare':select('snare_one_shot',rng,1),'hat':select('hat_one_shot',rng,.65),'clap':select('clap_one_shot',rng,1)}
 sounds={k:load(v) for k,v in rows.items()}
 def place(track,sound,time,gain):
  start=int(round(time*SR));length=min(len(sound),n-start)
  if start>=0 and length>0:track[start:start+length]+=sound[:length]*gain
 def fade(x):
  x=x.copy();a=min(len(x)//3,192);b=min(len(x)//3,1200)
  if a:x[:a]*=np.linspace(0,1,a)
  if b:x[-b:]*=np.linspace(1,0,b)
  return x
 for bar in range(bars):
  chord=plan['chords'][bar%4];root=24+chord['root_pc'];root+=12 if root<28 else 0
  hz=440*2**((root-69)/12);ratio=hz/rows['bass']['tuning']['hz'];numerator=int(round(10000/ratio))
  tonal=resample_poly(sounds['bass'],numerator,10000).astype('float32')
  patterns=[[(0,1.25,.83),(1.5,.5,.58),(2.5,1.25,.75)],[(0,1.75,.78),(2,.75,.74),(3,.65,.62)],[(0,.6,.82),(.75,.7,.60),(2,1.1,.78),(3.5,.45,.58)],[(0,2.2,.83),(2.75,1.1,.71)],[(0,.9,.81),(1.25,1.2,.65),(2.75,1.05,.78)],[(0,1.1,.8),(1.5,.4,.6),(2.0,.9,.7),(3.25,.6,.63)]]
  pattern=patterns[(plan['groove_index']+bar%2)%len(patterns)]
  for offset,dur,velocity in pattern:
   place(tracks['bass'],fade(tonal[:int(dur*beat*SR)]),(bar*4+offset)*beat,velocity*.6)
   events.append({'role':'bass','bar':bar,'beat':offset,'midi':root,'hz':round(hz,5),'duration_beats':dur})
   place(tracks['drums'],fade(sounds['kick'][:21600]),(bar*4+offset)*beat,.5)
  backbeats=[2] if plan['bpm']>=125 and re.search(r'trap|drill|трэп|дрилл',str(style),re.I) else [1,3]
  for off in backbeats:
   place(tracks['drums'],fade(sounds['snare'][:19200]),(bar*4+off)*beat,.28)
   place(tracks['drums'],fade(sounds['clap'][:14400]),(bar*4+off)*beat,.10)
  hat_patterns=[[0,.5,1,1.5,2,2.5,3,3.5],[0,.75,1.5,2,2.75,3.5],[0,.5,.75,1.5,2,2.5,3.25,3.5]]
  for tick,off in enumerate(hat_patterns[plan['groove_index']%3]):place(tracks['drums'],fade(sounds['hat'][:6240]),(bar*4+off)*beat,float(rng.uniform(.055,.105)))
  if bar%4==3:
   for off in [3.25,3.5,3.75]:place(tracks['drums'],fade(sounds['hat'][:3360]),(bar*4+off)*beat,.055)
 # No fixed toy-pluck melody: the requested instruments are left to the composer.
 tracks['bass']=sosfiltfilt(butter(2,[22,1300],btype='bandpass',fs=SR,output='sos'),tracks['bass']).astype('float32')
 mix=sum(tracks.values());gain=.84/max(np.max(np.abs(mix)),.001);mix*=gain
 for name,x in tracks.items():sf.write(folder/(name+'.wav'),x*gain,SR,subtype='PCM_24')
 sf.write(out,np.column_stack((mix,mix)),SR,subtype='PCM_24')
 if any(e['midi']%12 not in plan['scale_pcs'] for e in events):raise AssertionError('Out-of-key rendered note')
 info={'kind':'independent_arrangement21','plan':plan,'reference_key':plan['key'],'bpm':plan['bpm'],'seconds':n/SR,'samples':{k:v['path'] for k,v in rows.items()},'source_tuning':rows['bass']['tuning'],'events':events,'out_of_scale_note_events':0,'sample_rate':SR,'private_stems':str(folder),'usage':'Acoustic and harmonic guidance; not a guarantee of final generated notes.','acoustic_quality_verified':False}
 meta.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');return {'path':str(out),**info}

def make_reference(style,bpm=0,key='',seed=None):return render_reference(style,choose_plan(style,bpm,key,seed))

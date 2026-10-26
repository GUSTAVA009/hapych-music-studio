"""Local sample-based acoustic reference, not a layer blindly mixed into a song.
SampleRadar samples remain private. Only composed music is exported.
"""
from pathlib import Path
import hashlib,json,re
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfiltfilt,resample_poly
from math import gcd
ROOT=Path.home()/'Music Studio';LIB=ROOT/'Sound Library';SR=48000

def needs_808(style):
    text=str(style)
    if re.search(r'(?:без|no|without)\s+(?:808|sub\s*bass)',text,re.I):return False
    return bool(re.search(r'\b(?:808|trap|трэп|треп|drill|дрилл)\b',text,re.I))

def read_sample(path):
    a,sr=sf.read(str(path),dtype='float32',always_2d=True);a=a.mean(axis=1)
    if sr!=SR:
        g=gcd(sr,SR);a=resample_poly(a,SR//g,sr//g)
    return a.astype('float32')

def sample_frequency(audio):
    part=audio[int(SR*.12):min(len(audio),int(SR*.8))]
    if len(part)<2048:raise ValueError('808 sample too short for tuning')
    n=262144;power=np.abs(np.fft.rfft(part*np.hanning(len(part)),n))
    f=np.fft.rfftfreq(n,1/SR);mask=(f>=28)&(f<=150)
    return float(f[np.flatnonzero(mask)[np.argmax(power[mask])]])

def make_reference(style,bpm=0,key=''):
    if not needs_808(style):return None
    tempo=float(bpm or 0)
    if not tempo:
        match=re.search(r'\b(\d{2,3})\s*(?:BPM|уд/?мин)',str(style),re.I)
        tempo=float(match[1]) if match else 140.0 if re.search(r'trap|drill|трэп|дрилл',str(style),re.I) else 100.0
    tempo=max(40,min(200,tempo));beat=60/tempo
    token=hashlib.sha256((str(style)+'|'+str(tempo)+'|'+key+'|reference18-v1').encode()).hexdigest()[:16]
    cache=LIB/'references';cache.mkdir(exist_ok=True);out=cache/(token+'.wav')
    meta=out.with_suffix('.json')
    if out.is_file() and meta.is_file():return {'path':str(out),**json.loads(meta.read_text(encoding='utf-8'))}
    sources=sorted(p for p in (LIB/'808_weight').rglob('808W_SrcA-06.wav') if '__MACOSX' not in p.parts)
    if not sources:raise FileNotFoundError('Локальный сэмпл 808 не установлен.')
    sample=read_sample(sources[0]);fundamental=sample_frequency(sample)
    sample-=sample.mean();sample/=max(float(np.max(np.abs(sample))),1e-6)
    tonic=9
    m=re.match(r'^([A-G])([#b]?)',key)
    if m:tonic=({'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[m[1]]+{'':0,'#':1,'b':-1}[m[2]])%12
    root=24+tonic
    if root<28:root+=12
    bars=8;length=int(bars*4*beat*SR);bass=np.zeros(length,np.float32);drums=np.zeros(length,np.float32)
    def put(track,sound,position,gain=1):
        at=int(round(position*SR));n=min(len(sound),len(track)-at)
        if at>=0 and n>0:track[at:at+n]+=sound[:n]*gain
    rng=np.random.default_rng(1818)
    t=np.arange(int(.34*SR))/SR;freq=48+110*np.exp(-t*55);kick=np.sin(2*np.pi*np.cumsum(freq)/SR)*np.exp(-t*16)
    t=np.arange(int(.18*SR))/SR;noise=rng.normal(0,1,len(t));snare=sosfiltfilt(butter(2,1400,'highpass',fs=SR,output='sos'),noise)*np.exp(-t*24)
    snare/=max(abs(snare).max(),1e-6)
    t=np.arange(int(.055*SR))/SR;hat=sosfiltfilt(butter(2,7000,'highpass',fs=SR,output='sos'),rng.normal(0,1,len(t)))*np.exp(-t*75)
    hat/=max(abs(hat).max(),1e-6)
    events=[]
    for bar in range(bars):
        note=root+[0,0,-2,-4][bar%4];hz=440*2**((note-69)/12)
        for off,beats,velocity in [(0,1.4,.82),(1.75,.65,.64),(2.5,1.25,.76)]:
            count=int(beats*beat*SR);positions=np.arange(count)*hz/fundamental
            tone=np.interp(positions,np.arange(len(sample)),sample,left=0,right=0).astype(np.float32)
            fade=min(count//3,int(.025*SR));tone[:fade]*=np.linspace(0,1,fade);tone[-fade:]*=np.linspace(1,0,fade)
            start=(bar*4+off)*beat;put(bass,tone,start,velocity);events.append({'time':round(start,4),'midi':note,'frequency_hz':round(hz,2)})
        for off in (0,1.75,2.5):put(drums,kick,(bar*4+off)*beat,.7)
        for off in (1,3):put(drums,snare,(bar*4+off)*beat,.45)
        for tick in range(8):put(drums,hat,(bar*4+tick*.5)*beat,.14 if tick%2 else .20)
        if bar%2:
            for tick in (3.25,3.5,3.75):put(drums,hat,(bar*4+tick)*beat,.10)
    bass=sosfiltfilt(butter(2,700,'lowpass',fs=SR,output='sos'),bass).astype(np.float32)
    mix=.8*bass+drums;peak=max(float(np.max(np.abs(mix))),1e-6);mix*=.88/peak
    stereo=np.column_stack((mix,mix));sf.write(out,stereo,SR,subtype='PCM_24')
    info={'kind':'808_acoustic_reference','sample':str(sources[0].relative_to(LIB)),'sample_base_hz':round(fundamental,3),'bpm':tempo,'reference_key':key or 'A minor (reference only; not forced on song)','seconds':length/SR,'events':events,'usage':'Global acoustic guidance for ACE-Step; not a guaranteed final bass stem.','license_manifest':str(LIB/'licenses.json')}
    meta.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'path':str(out),**info}

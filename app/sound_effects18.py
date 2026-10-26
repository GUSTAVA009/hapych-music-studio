"""Explicit post-production effects on a measured section timeline.
No timing guesses from word counts. Model LRC is alignment, not proof of sung words.
"""
from pathlib import Path
from difflib import SequenceMatcher
from math import gcd
import re,json,subprocess
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=Path.home()/'Music Studio';LIB=ROOT/'Sound Library';SR=48000
SUPPORTED={'sea surf':'sea_surf.wav'}

def normalize(text):
    return ' '.join(re.findall(r'[a-zа-яё0-9]+',re.sub(r'\[[^\]]*\]','',str(text)).casefold().replace('ё','е')))

def parse_lrc(value):
    entries=[]
    for line in str(value or '').splitlines():
        matches=list(re.finditer(r'\[(\d{1,3}):(\d{1,2}(?:[.,]\d+)?)\]',line))
        if not matches:continue
        text=re.sub(r'\[\d{1,3}:\d{1,2}(?:[.,]\d+)?\]','',line).strip();clean=normalize(text)
        if not clean:continue
        # Native ACE-Step LRC may include both start and end on one line.
        # The second timestamp is not a second performance of the same words.
        m=matches[0]
        entry={'time':int(m[1])*60+float(m[2].replace(',','.')),'text':text,'normalized':clean}
        if len(matches)>1:
            tail=matches[1];entry['end']=int(tail[1])*60+float(tail[2].replace(',','.'))
        entries.append(entry)
    return sorted(entries,key=lambda x:x['time'])

def planned_effects(sections):
    result=[]
    for i,sec in enumerate(sections or []):
        for effect in sec.get('effects',[]):
            raw='; '.join(v.get('text','') for v in sec.get('instructions',[]))
            if effect=='sea surf' and re.search(r'(?:без|no|without)\s+(?:шума?\s+моря|прибоя|sea\s+surf|ocean)',raw,re.I):continue
            result.append({'section_id':sec['id'],'section':sec['section'],'section_index':i,'effect':effect,'supported':effect in SUPPORTED})
    return result

def resolve_effects(sections,lrc,duration):
    entries=parse_lrc(lrc);cursor=0;matches={};warnings=[]
    for index,sec in enumerate(sections):
        hits=[]
        for line in sec.get('lyrics','').splitlines():
            goal=normalize(line)
            if not goal:continue
            choices=[]
            for k in range(cursor,len(entries)):
                val=entries[k]['normalized'];score=SequenceMatcher(None,goal,val).ratio()
                if score>=.76:choices.append((score,k))
            if not choices:continue
            # Prefer the earliest close match; repeated choruses remain separate.
            best=max(v[0] for v in choices);k=next(k for score,k in choices if score>=max(.76,best-.04))
            if 0<=entries[k]['time']<duration:hits.append(entries[k]['time']);cursor=k+1
        if hits:matches[index]={'first':min(hits),'last':max(hits)}
    # Prefer explicit timed section markers over the first sung word.
    # Otherwise an effect can bleed into the next section's instrumental pickup.
    from studio_text_v4 import split_header
    headers=[]
    for line in str(lrc or '').splitlines():
        stamp=re.search(r'\[(\d{1,3}):(\d{1,2}(?:[.,]\d+)?)\]',line)
        if not stamp:continue
        rest=re.sub(r'\[\d{1,3}:\d{1,2}(?:[.,]\d+)?\]','',line).strip()
        tag=re.fullmatch(r'\[([^\]]+)\]',rest)
        if tag:
            section,_=split_header(tag[1])
            if section:headers.append((section,int(stamp[1])*60+float(stamp[2].replace(',','.'))))
    header_cursor=0
    for i,sec in enumerate(sections):
        for h in range(header_cursor,len(headers)):
            name,t=headers[h]
            if name==sec['section'] and 0<=t<duration:
                matches.setdefault(i,{})['first']=t
                header_cursor=h+1
                break
    events=[]
    for item in planned_effects(sections):
        i=item['section_index'];sec=sections[i]
        if not item['supported']:
            warnings.append(sec['section']+': нет проверенного сэмпла для '+item['effect']);continue
        raw='; '.join(d['text'] for d in sec.get('instructions',[]))
        explicit=re.search(r'(?<!\d)(\d{1,2}):(\d{2}(?:\.\d+)?)\s*[-–—]\s*(\d{1,2}):(\d{2}(?:\.\d+)?)',raw)
        basis='model_lrc_alignment'
        if explicit:
            start=int(explicit[1])*60+float(explicit[2]);end=int(explicit[3])*60+float(explicit[4]);basis='explicit_user_interval'
        elif len(sections)==1:
            start,end=0.,duration;basis='single_section_full_timeline'
        else:
            start=0. if i==0 and sec['section'].startswith('Intro') else matches.get(i,{}).get('first')
            if i+1==len(sections):end=duration
            else:end=matches.get(i+1,{}).get('first')
        if start is None or end is None or not (0<=start<end<=duration+.1) or end-start<.3:
            warnings.append(sec['section']+': не удалось определить границы эффекта. Звук не вставлен наугад; укажи интервал 00:00-00:08 в скобках.');continue
        events.append(dict(item,start=round(start,4),end=round(min(end,duration),4),timing_basis=basis))
    return events,warnings

def decode(path):
    data,sr=sf.read(str(path),dtype='float32',always_2d=True)
    if not np.all(np.isfinite(data)):raise ValueError('Некорректные отсчёты аудио')
    if sr!=SR:
        g=gcd(SR,sr);data=resample_poly(data,SR//g,sr//g,axis=0).astype(np.float32)
    if data.shape[1]==1:data=np.repeat(data,2,axis=1)
    return data[:,:2]

def fit_effect(sample,count):
    if count<=len(sample):return sample[:count].copy()
    out=np.zeros((count,2),np.float32);weights=np.zeros(count,np.float32);overlap=min(SR,len(sample)//4);step=len(sample)-overlap
    for pos in range(0,count,step):
        n=min(len(sample),count-pos);env=np.ones(n,np.float32)
        if pos:env[:min(overlap,n)]*=np.linspace(0,1,min(overlap,n))
        if pos+n<count:env[-overlap:]*=np.linspace(1,0,overlap)
        out[pos:pos+n]+=sample[:n]*env[:,None];weights[pos:pos+n]+=env
    return out/np.maximum(weights[:,None],1e-6)

def render_effects(source,output_master,prepared,lrc,stem_path):
    music=decode(source);duration=len(music)/SR
    events,warnings=resolve_effects(prepared.get('sections',[]),lrc,duration)
    fx=np.zeros_like(music);reports=[]
    for event in events:
        sample_path=LIB/SUPPORTED[event['effect']]
        if not sample_path.is_file():raise FileNotFoundError('Сэмпл '+event['effect']+' отсутствует; исходник сохранён.')
        start=int(round(event['start']*SR));end=min(len(music),int(round(event['end']*SR)));count=end-start
        chunk=fit_effect(decode(sample_path),count)
        sample_rms=float(np.sqrt(np.mean(chunk.astype(np.float64)**2)))
        music_rms=float(np.sqrt(np.mean(music[start:end].astype(np.float64)**2)))
        target=np.clip(music_rms*10**(-12/20),10**(-35/20),10**(-23/20))
        gain=min(target/max(sample_rms,1e-9),.30/max(float(abs(chunk).max()),1e-9))
        envelope=np.ones(count,np.float32);fadein=min(count//3,int(.35*SR));fadeout=min(count//3,int(.75*SR))
        envelope[:fadein]=np.sin(np.linspace(0,np.pi/2,fadein))**2;envelope[-fadeout:]=np.cos(np.linspace(0,np.pi/2,fadeout))**2
        chunk*=gain*envelope[:,None];fx[start:end]+=chunk
        reports.append(dict(event,sample=str(sample_path),gain_db=round(float(20*np.log10(max(gain,1e-9))),2),effect_rms_dbfs=round(float(20*np.log10(max(np.sqrt(np.mean(chunk.astype(np.float64)**2)),1e-9))),2)))
    mix=music+fx;peak=float(abs(mix).max());attenuation=min(1.,.96/max(peak,1e-9));mix*=attenuation
    output_master=Path(output_master);output_master.parent.mkdir(parents=True,exist_ok=True);tmp=output_master.with_suffix('.fx-part.wav')
    sf.write(tmp,mix,SR,subtype='PCM_24');tmp.replace(output_master)
    stem_path=Path(stem_path);stem_path.parent.mkdir(parents=True,exist_ok=True);sf.write(stem_path,fx,SR,subtype='PCM_24')
    return {'effects_requested':len(planned_effects(prepared.get('sections',[]))),'effects_applied':reports,'warnings':warnings,'duration_seconds':duration,'sample_rate':SR,'effects_stem':str(stem_path),'master':str(output_master),'peak_dbfs':round(float(20*np.log10(max(abs(mix).max(),1e-9))),2),'global_attenuation_db':round(float(20*np.log10(attenuation)),2),'acoustic_quality_verified':False}

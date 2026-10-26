"""Music Studio: explicit SFX cues, repeatable licensed/local sample placement.
SFXs are never sent as sung text. Missing recordings are reported explicitly.
"""
from pathlib import Path
from difflib import SequenceMatcher
from math import gcd
import json,re
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt
from sound_bank29 import NAMES, install
from sound_effects18 import parse_lrc,normalize
from studio_text_v4 import split_header
from sound_catalog30 import match as match_installed, asset as installed_asset, stats as catalog_stats
from sound_stage31 import shape as balance_sfx, finish as finish_sfx_mix
from sound_quality32 import preferred_path as preferred_recorded, recognize as recognize_recorded
from sound_arranger35 import arrange_event as arrange_music_event, music_tied_ambience
ROOT=Path.home()/"Music Studio";LIB=ROOT/"Sound Library";BANK=LIB/"sfx";SR=48000
RULES=[
(r"alarm.*(?:stop|off|выключ)", "alarm_stop"),
(r"engine.*(?:shut|stop|off)|глуш.*двигател", "engine_stop"),
(r"rain.*(?:fade|затиха)|дожд.*затиха", "rain_asphalt"),
(r"police.*radio|полицейск.*раци", "police_radio"),
(r"police.*siren|\bsirens?\b|сирен|мигалк", "police_siren"),
(r"car.*unlock|открыт.*машин.*сигнал", "car_unlock"),
(r"car.*door|door.*open|двер.*откр", "car_door"),
(r"car.*pass|pass.*car|проезжа.*машин|проезж.*автомоб", "car_pass"),
(r"engine.*start|ignition|запуск.*двигател|завод.*машин", "engine_start"),
(r"engine.*rev|газует|перегазов", "engine_rev"),
(r"station.*tun|настройк.*радио|поиск.*станци", "station_tuning"),
(r"radio.*static|радиопомех|шум.*радио", "radio_static"),
(r"phone.*vibrat|вибрац.*телефон", "phone_vibrate"),
(r"phone.*ring|телефон.*звон|звонок.*телефон", "phone_ring"),
(r"cards.*shuff|перемеш.*карт|тасов.*карт", "cards_shuffle"),
(r"cards.*slap|карт.*стол", "cards_slap"),
(r"car.*stereo|музык.*из.*машин", "car_stereo"),
(r"lighter|зажигал", "lighter_click"),
(r"clock.*tick|тикани.*час", "clock_tick"),
(r"tire.*rain|шин.*дожд|колес.*луж", "tires_rain"),
(r"wind.*car|ветер.*машин|ветер.*окн", "wind_car"),
(r"coin|монет", "coins_drop"),
(r"hookah.*bubbl|кальян.*бульк", "hookah_bubbles"),
(r"alarm.*clock|будильник", "alarm_clock"),
(r"tape.*click|щелч.*пленк", "tape_click"),
(r"vinyl.*crackle|треск.*винил", "vinyl_crackle"),
(r"rain|дожд", "rain_asphalt"),
(r"bass.*drop|басов.*дроп", "bass_impact"),
(r"footstep|шаги", "footsteps"),
(r"key.*jangl|ключ.*звени", "keys_jangle"),
(r"door.*knock|стук.*двер", "door_knock"),
(r"glass.*clink|стакан.*звен", "glass_clink"),
]
UNSUPPORTED=[r"\blaughter\b|\bсмех\b",r"room.*chatter|разговор.*толп|разговор.*комнат"]
AMBIENCE={"rain_asphalt","tires_rain","wind_car","vinyl_crackle","car_stereo","car_pass",
          "night_ambience","record_player_loop","water_stream",
          "city_traffic","construction_site","factory_machinery","running_water",
          "city_ambience","wind_gust","crowd_shouting","room_laughter_chatter",
          "storm_siren","radio_noise"}
KENNEY_CC0={"cards_shuffle":("casino","card-shuffle.ogg"),"cards_slap":("casino","card-place-1.ogg"),
           "coins_drop":("rpg","handleCoins.ogg"),"car_door":("rpg","doorOpen_1.ogg"),
           "footsteps":("rpg","footstep00.ogg"),"glass_clink":("interface","glass_001.ogg"),
           "tape_click":("rpg","metalClick.ogg")}
REAL_CC0={
    "rain_asphalt":("rain","1.ogg"),
    "engine_start":("car_engine_start.wav",),
    "car_door":("car_door_open.wav",),
    "car_pass":("car_passing.wav",),
}
def _asset_path(name,variant=0):
    original_recording=preferred_recorded(name,variant)
    if original_recording is not None:return original_recording
    if name=="room_laughter_chatter":
        from sound_room30 import build
        if not (BANK/"room_laughter_chatter.wav").is_file():build()
        return BANK/"room_laughter_chatter.wav"
    chosen=installed_asset(name,variant)
    if chosen is not None:return chosen
    if name=="sea surf":return LIB/"sea_surf.wav"
    if name in REAL_CC0:
        real=LIB/"external_cc0"/"realworld"
        for step in REAL_CC0[name]:real=real/step
        if real.is_file():return real
    item=KENNEY_CC0.get(name)
    if item:
        hits=list((LIB/"external_cc0"/item[0]).rglob(item[1]))
        if hits:return hits[0]
    return BANK/(name+".wav")
def canonical(desc):
    desc=str(desc).strip()
    clean=re.sub(r"\b(?:sfx|fx)\s*[:：-]","",desc,flags=re.I)
    clean=re.sub(r"\b(?:at|@)\s*(?:\d{1,2}:)?\d{1,2}(?:\.\d+)?\b","",clean,flags=re.I)
    installed=match_installed(clean)
    if installed:return installed
    recorded=recognize_recorded(clean)
    if recorded:return recorded
    for pat in UNSUPPORTED:
        if re.search(pat,clean,re.I):return None
    for pat,kind in RULES:
        if re.search(pat,clean,re.I):return kind
    if re.search("sea.*surf|шум моря|прибой",clean,re.I):return "sea surf"
    return None
def split_desc(raw):
    # Commas denote sequential physical events, but hyphenated style descriptors do not.
    parts=re.split(r",\s*|;\s*",raw)
    return [p.strip() for p in parts if p.strip()]
def planned_effects(sections):
    result=[]
    for i,sec in enumerate(sections or []):
        explicit=[]
        for instr in sec.get("instructions",[]):
            desc=str(instr.get("text","")).strip()
            m=re.match(r"^(?:SFX|FX)\s*(?:[:：-]\s*)?(.+)$",desc,re.I)
            if not m:m=re.match(r"^(.+?)\s+(?:SFX|FX)$",desc,re.I)
            if not m:continue
            for j,part in enumerate(split_desc(m[1])):
                kind=canonical(part)
                # In a combined car sequence, bare 'door opens' is the car door.
                if kind=='door_open' and re.search(r'\bcar\b|машин|автомоб',m[1],re.I):
                    kind='car_door'
                obj={"section_id":sec["id"],"section":sec["section"],"section_index":i,
                     "effect":kind or part,"requested":part,"supported":bool(kind and _asset_path(kind).is_file()),
                     "line":instr.get("line",0),"sequence":j,"timing_basis":"pending"}
                explicit.append(obj)
        result.extend(explicit)
        # Sound descriptions in section headings are musical guidance, except ambience.
        raw="; ".join(v.get("text","") for v in sec.get("instructions",[]) if not (re.match(r"^\s*(?:SFX|FX)\b",v.get("text",""),re.I) or re.search(r"\b(?:SFX|FX)\s*$",v.get("text",""),re.I)))
        legacy=[]
        if re.search(r"vinyl.*crackle|треск.*винил",raw,re.I):legacy.append("vinyl_crackle")
        if re.search(r"sea.*surf|шум моря|прибой",raw,re.I):legacy.append("sea surf")
        if re.search(r"tape.*click|щелч.*пленк",raw,re.I):legacy.append("tape_click")
        if re.search(r"heavy\s+bass\s+drop|massive\s+bass\s+drop",raw,re.I):legacy.append("bass_impact")
        for kind in legacy:
            if not any(x["effect"]==kind for x in explicit):
                result.append({"section_id":sec["id"],"section":sec["section"],"section_index":i,
                               "effect":kind,"requested":kind,"supported":True,"line":0,"sequence":0})
    return result
def _guess_boundaries(sections,duration):
    weights=[]
    for sec in sections:
        lyric=sec.get("lyrics","")
        syllables=len(re.findall(r"[аеёиоуыэюяaeiouy]",lyric,re.I))
        weights.append(max(4.5,syllables*.25+2.5))
    cumulative=np.cumsum([0]+weights,dtype=float)
    return list(cumulative/max(1,cumulative[-1])*duration)
def _section_lines(sections,raw):
    markers=[]
    for i,line in enumerate(raw.splitlines(),1):
        line=line.strip()
        m=re.fullmatch(r"\[([^\]]+)\]",line)
        if m and split_header(m[1])[0]:markers.append(i)
    if len(markers)!=len(sections):
        return [(0,len(raw.splitlines())+1)]*len(sections)
    return [(markers[i],markers[i+1] if i+1<len(markers) else len(raw.splitlines())+1) for i in range(len(markers))]
def _sections_from_lrc(sections,lrc,duration):
    entries=parse_lrc(lrc)
    fallback=_guess_boundaries(sections,duration)
    if not entries:return fallback,False
    cursor=0;located={}
    for i,sec in enumerate(sections):
        lines=[normalize(x) for x in sec.get("lyrics","").splitlines() if normalize(x)]
        for line in lines[:7]:
            find=None
            for k in range(cursor,len(entries)):
                if SequenceMatcher(None,line,entries[k]["normalized"]).ratio()>=.75:
                    find=k;break
            if find is not None:
                located[i]=entries[find]["time"]
                cursor=find+1
                break
    if not located:return fallback,False
    aligned=fallback[:]
    for i,t in located.items():aligned[i]=min(max(0,t),duration-.1)
    aligned[0]=min(aligned[0],fallback[0]+3)
    aligned[-1]=duration
    # Never accept a non-monotonic reconstructed section clock.
    if any(aligned[i+1]<=aligned[i]+.1 for i in range(len(sections))):
        return fallback,False
    return aligned,True
def _explicit_time(desc):
    match=re.search(r"(?:@|at\s+)(\d{1,2}):(\d{2}(?:\.\d+)?)",desc,re.I)
    if match:return int(match[1])*60+float(match[2])
    return None
def resolve_effects(sections,lrc,duration,raw_lyrics=""):
    plans=planned_effects(sections)
    if not sections:return [],[]
    bounds,used_lrc=_sections_from_lrc(sections,lrc,duration)
    line_bounds=_section_lines(sections,raw_lyrics)
    events=[];warnings=[];sequences={}
    for plan in plans:
        if not plan["supported"]:
            warnings.append(plan["section"]+": no local SFX sample for "+plan["requested"])
            continue
        i=plan["section_index"];start=bounds[i];end=bounds[i+1]
        lower,upper=line_bounds[i]
        cue_line=plan.get("line",0)
        timed=_explicit_time(plan["requested"])
        if timed is not None:
            at=timed;basis="explicit_timestamp"
        elif cue_line and lower<upper:
            ratio=np.clip((cue_line-lower)/max(1,upper-lower),0,.96)
            at=start+.08+ratio*max(.1,end-start-.4)
            basis="lrc_section_estimate" if used_lrc else "section_proportional_estimate"
        else:
            at=start+.12;basis="lrc_section_estimate" if used_lrc else "section_proportional_estimate"
        key=(i,cue_line)
        shift=sequences.get(key,0)
        at+=shift*.8
        sequences[key]=shift+1
        if not (0<=at<duration):
            warnings.append(plan["section"]+": SFX outside track: "+plan["requested"])
            continue
        # No guess is described as sample-accurate lyric alignment.
        kind=plan["effect"]
        # Atmospheres should establish a scene, not collapse to a one-second burst
        # simply because their lyric cue appears near the end of an intro.
        # Preserve explicit timing and do not extend beyond the song boundary.
        length=min(12.0,max(4.0,end-at)) if kind in AMBIENCE else None
        # Phone and alarm samples already contain several complete ring cycles.
        repeats=3 if plan["effect"] not in ("phone_ring","alarm_clock") and re.search(r"three\s+times|три\s+раз",plan["requested"],re.I) else 1
        events.append(dict(plan,start=round(float(at),3),duration=length,
                           repeat=repeats,timing_basis=basis))
    return events,warnings
def decode(p):
    a,sr=sf.read(str(p),dtype="float32",always_2d=True)
    if not np.all(np.isfinite(a)):raise ValueError("Invalid audio samples")
    if sr!=SR:
        g=gcd(sr,SR);a=resample_poly(a,SR//g,sr//g,axis=0)
    if a.shape[1]==1:a=np.repeat(a,2,axis=1)
    return a[:,:2].astype(np.float32)
def _loop_sample(a,n):
    if len(a)>=n:return a[:n].copy()
    overlap=min(int(SR*.13),max(1,len(a)//8))
    step=len(a)-overlap
    out=np.zeros((n,2),np.float32);weights=np.zeros(n,np.float32)
    for pos in range(0,n,step):
        m=min(len(a),n-pos);env=np.ones(m,np.float32)
        if pos:env[:min(m,overlap)]=np.linspace(0,1,min(m,overlap))
        if pos+m<n:env[-min(m,overlap):]*=np.linspace(1,0,min(m,overlap))
        out[pos:pos+m]+=a[:m]*env[:,None];weights[pos:pos+m]+=env
    return out/np.maximum(weights[:,None],1e-4)
def render_effects(source,output_master,prepared,lrc,stem_path):
    install()  # Only missing synthetic examples; never overwrite imported WAVs.
    music=decode(source)
    duration=len(music)/SR
    sections=prepared.get("sections",[])
    plans=planned_effects(sections)
    events,warnings=resolve_effects(sections,lrc,duration,prepared.get("raw_lyrics",""))
    fx=np.zeros_like(music);duck=np.zeros(len(music),dtype=np.float32);reports=[]
    for event in events:
        event=arrange_music_event(event,prepared,duration)
        name=event["effect"]
        sample_path=_asset_path(name,variant=event["section_index"]+event.get("line",0))
        if not sample_path.is_file():
            warnings.append("Missing sample: "+str(sample_path));continue
        at=int(event["start"]*SR)
        if at>=len(fx):continue
        sample=decode(sample_path)
        if event["duration"] is not None:count=min(len(music)-at,int(event["duration"]*SR))
        else:count=min(len(music)-at,len(sample)*event["repeat"])
        if count<2:continue
        if event["repeat"]>1 and event["duration"] is None:
            pieces=np.zeros((count,2),np.float32)
            for k in range(event["repeat"]):
                start=k*len(sample);stop=min(start+len(sample),count)
                if start<count:pieces[start:stop]=sample[:stop-start]
            chunk=pieces
        else:
            if name=="car_pass" and len(sample)>count:
                # Keep the audible vehicle approach/pass, not a long silent head.
                scan_step=max(1,int(SR*.25))
                best=0;best_rms=-1.
                for k in range(0,len(sample)-count+1,scan_step):
                    probe=sample[k:k+count:96]
                    score=float(np.mean(probe*probe))
                    if score>best_rms:best,best_rms=k,score
                chunk=sample[best:best+count].copy()
            else:chunk=_loop_sample(sample,count)
        if name not in ("engine_start","engine_rev","engine_stop","car_stereo","bass_impact"):
            sos=butter(1,90,btype="highpass",fs=SR,output="sos")
            chunk=sosfilt(sos,chunk,axis=0).astype("float32")
        is_ambient=name in AMBIENCE
        if is_ambient and event.get("beat_alignment"):
            chunk,levels=music_tied_ambience(chunk,music[at:at+count],event,SR)
        else:
            chunk,levels=balance_sfx(chunk,music[at:at+count],name,is_ambient)
        fx[at:at+count]+=chunk
        if not is_ambient:
            # Brief, smooth music ducking helps short Foley stay audible.
            envelope=np.minimum(1.0,np.arange(count,dtype=np.float32)/max(1,int(.07*SR)))
            envelope*=np.minimum(1.0,np.arange(count,dtype=np.float32)[::-1]/max(1,int(.22*SR)))
            duck[at:at+count]=np.maximum(duck[at:at+count],envelope)
        reports.append({**event,"sample":str(sample_path),**levels,
                        "rendered_seconds":round(count/SR,3)})
    # Position and gain effects separately, then blend with transparent headroom.
    mix,mix_info=finish_sfx_mix(music,fx,duck)
    output_master=Path(output_master);output_master.parent.mkdir(parents=True,exist_ok=True)
    tmp=output_master.with_suffix(".fx-part.wav")
    sf.write(tmp,mix,SR,subtype="PCM_24");tmp.replace(output_master)
    stem_path=Path(stem_path);stem_path.parent.mkdir(parents=True,exist_ok=True)
    sf.write(stem_path,fx,SR,subtype="PCM_24")
    return {"effects_requested":len(plans),"effects_applied":reports,"effects_missing":[p["requested"] for p in plans if not p["supported"]],
            "warnings":warnings,"master":str(output_master),"effects_stem":str(stem_path),
            "duration_seconds":duration,"sample_rate":SR,
            "peak_dbfs":round(float(20*np.log10(max(1e-8,float(np.max(np.abs(mix)))))),2),
            "global_attenuation_db":mix_info["master_attenuation_db"],
            "mixing":mix_info,"sfx_balance_revision":"sound_arranger35_music_following_bar_grids",
            "stereo_fx":True,"sample_provenance":"CC0 field recordings and locally synthesized Foley-style placeholders",
            "timing_note":"User timestamps accurate; untimed cues estimated from section placement; no forced word alignment",
            "acoustic_quality_verified":False}

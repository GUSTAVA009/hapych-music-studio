"""Original, deterministic Foley-style synthetic audio, not recordings of real events.
Keeps provenance explicit. Place real licensed WAV/OGG overrides in Sound Library/sfx.
"""
from pathlib import Path
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt
SR=48000
DEST=Path.home()/"Music Studio"/"Sound Library"/"sfx"
NAMES=["rain_asphalt","police_siren","car_unlock","car_door","engine_start",
"radio_static","station_tuning","phone_ring","cards_shuffle","car_stereo",
"phone_vibrate","lighter_click","clock_tick","engine_rev","police_radio",
"tires_rain","wind_car","coins_drop","cards_slap","hookah_bubbles",
"alarm_clock","engine_stop","alarm_stop","tape_click","vinyl_crackle",
"bass_impact","footsteps","keys_jangle","door_knock","glass_clink"]
def tone(n,f,phase=0):
    t=np.arange(n,dtype=np.float64)/SR
    if np.isscalar(f):return np.sin(2*np.pi*f*t+phase)
    return np.sin(2*np.pi*np.cumsum(f)/SR+phase)
def noise(rng,n,low=80,high=12000):
    x=rng.normal(0,1,n)
    if high<SR/2:
        x=sosfilt(butter(2,high,btype="low",fs=SR,output="sos"),x)
    if low>0:
        x=sosfilt(butter(1,low,btype="high",fs=SR,output="sos"),x)
    return x/(np.std(x)+1e-9)
def pulse(n,start,span,amp,typ="noise",frequency=400,rng=None):
    out=np.zeros(n,np.float64);p=int(start*SR);m=min(n-p,int(span*SR))
    if m<=1 or p<0:return out
    t=np.arange(m)/SR; env=np.exp(-t/max(.005,span/5))
    if typ=="tone":signal=tone(m,frequency)
    else:signal=noise(rng,m,low=100,high=8000)
    out[p:p+m]=amp*env*signal
    return out
def make(name):
    seed=129000+NAMES.index(name);rng=np.random.default_rng(seed)
    lengths={"rain_asphalt":7,"police_siren":5,"car_unlock":.65,"car_door":1.2,
    "engine_start":4.5,"radio_static":3,"station_tuning":3.5,"phone_ring":5,
    "cards_shuffle":2,"car_stereo":5,"phone_vibrate":2,"lighter_click":1,
    "clock_tick":4,"engine_rev":4,"police_radio":3,"tires_rain":6,"wind_car":6,
    "coins_drop":2,"cards_slap":.85,"hookah_bubbles":4,"alarm_clock":4,
    "engine_stop":2.4,"alarm_stop":.4,"tape_click":.3,"vinyl_crackle":7,
    "bass_impact":3,"footsteps":3,"keys_jangle":2,"door_knock":2,"glass_clink":1.5}
    n=int(lengths[name]*SR);t=np.arange(n,dtype=np.float64)/SR
    x=np.zeros(n,np.float64);y=np.zeros(n,np.float64)
    if name in ("rain_asphalt","tires_rain"):
        x=noise(rng,n,160,8000)*.22
        y=noise(rng,n,160,8000)*.22
        for k in range(240 if name=="rain_asphalt" else 160):
            at=rng.uniform(0,len(t)-.08)
            c=pulse(n,at,.045,rng.uniform(.009,.05),rng=rng)
            if rng.random()<.5:x+=c
            else:y+=c
        if name=="tires_rain":
            x+=noise(rng,n,35,350)*.10
            y+=noise(rng,n,40,420)*.10
    elif name=="police_siren":
        freq=730+280*np.sin(2*np.pi*.58*t)
        x=.16*tone(n,freq)+.035*tone(n,freq*2)
        y=np.roll(x,43)
        x*=np.minimum(1,t/.45)*np.minimum(1,(len(t)-1/SR-t)/.8)
        y*=np.minimum(1,t/.45)*np.minimum(1,(len(t)-1/SR-t)/.8)
    elif name in ("engine_start","engine_rev","engine_stop"):
        if name=="engine_start":f=36+55*np.clip((t-1)/3,0,1);env=np.minimum(1,t/.9)*np.minimum(1,(len(t)/SR-t)/.3)
        elif name=="engine_rev":f=55+100*np.sin(np.pi*np.clip(t/len(t)*SR,0,1));env=np.minimum(1,t/.18)*np.minimum(1,(len(t)/SR-t)/.3)
        else:f=75-55*np.clip(t/2.3,0,1);env=np.minimum(1,t/.1)*np.minimum(1,(len(t)/SR-t)/.12)
        x=(.25*tone(n,f)+.10*tone(n,2*f)+.04*tone(n,3*f)+.035*noise(rng,n,40,850))*np.clip(env,0,1)
        y=np.roll(x,67)
    elif name in ("radio_static","police_radio","station_tuning"):
        x=.14*noise(rng,n,250,10000)
        if name=="station_tuning":
            for k in range(9):x+=pulse(n,.17+k*.36,.18,.12,"tone",430+100*k,rng)
        if name=="police_radio":
            x*=.35+.65*(np.sin(2*np.pi*1.4*t)>-.2)
            for k in range(3):x+=pulse(n,.6+k*.85,.13,.20,"tone",930,rng)
        y=np.roll(x,199)
    elif name=="car_unlock":
        for at,f in ((.08,1100),(.25,1500)):
            x+=pulse(n,at,.19,.24,"tone",f,rng)
        y=np.roll(x,24)
    elif name in ("car_door","door_knock","cards_slap"):
        times=[.12,.38] if name=="door_knock" else [.13]
        for at in times:
            x+=pulse(n,at,.16,.3,rng=rng)+pulse(n,at,.22,.18,"tone",115,rng)
        y=np.roll(x,32)
    elif name in ("phone_ring","alarm_clock"):
        for at in ((.15,1.8,3.3) if name=="phone_ring" else (.1,.8,1.5,2.2,2.9)):
            if name=="phone_ring":
                mask=(t>=at)&(t<at+.72);x[mask]+=.16*(tone(n,425)[mask]+.3*tone(n,850)[mask])
            else:
                mask=(t>=at)&(t<at+.4);x[mask]+=.22*(tone(n,960)[mask]+.27*tone(n,1200)[mask])
        y=np.roll(x,12)
    elif name=="alarm_stop":
        x+=pulse(n,.035,.14,.12,rng=rng);y=x.copy()
    elif name=="phone_vibrate":
        for at in (.1,.55,1.1,1.55):
            mask=(t>=at)&(t<at+.18)
            x[mask]+=.20*tone(n,156)[mask]*(1+.25*tone(n,30)[mask])
        y=x*.7
    elif name in ("cards_shuffle","coins_drop","keys_jangle","glass_clink"):
        count={"cards_shuffle":36,"coins_drop":8,"keys_jangle":17,"glass_clink":4}[name]
        for k in range(count):
            at=rng.uniform(.05,len(t)-.15)
            if name=="cards_shuffle":a=pulse(n,at,.035,.06,rng=rng)
            else:
                f=rng.uniform(900,3300)
                a=pulse(n,at,.18,rng.uniform(.06,.15),"tone",f,rng)+pulse(n,at,.03,.08,rng=rng)
            if k%2:x+=a
            else:y+=a
    elif name=="lighter_click":
        x=pulse(n,.1,.035,.40,rng=rng)+pulse(n,.21,.22,.07,rng=rng);y=np.roll(x,19)
    elif name=="clock_tick":
        for k in range(8):
            a=pulse(n,.1+k*.5,.05,.2,rng=rng)
            if k%2:x+=a*.75
            else:y+=a
    elif name=="car_stereo":
        x=.22*tone(n,52)*(np.maximum(0,np.cos(2*np.pi*1.53*t))**12)
        x+=.04*noise(rng,n,250,2800)*(np.maximum(0,np.cos(2*np.pi*3.06*t))**8)
        y=np.roll(x,53)
    elif name=="wind_car":
        x=noise(rng,n,90,2600)*(.08+.06*np.sin(2*np.pi*.18*t))
        y=np.roll(x,1300)
    elif name=="hookah_bubbles":
        for k in range(45):
            at=rng.uniform(.1,len(t)-.15);f=rng.uniform(90,330)
            a=pulse(n,at,.13,rng.uniform(.07,.17),"tone",f,rng)
            if k%2:x+=a
            else:y+=a
    elif name=="tape_click":
        x=pulse(n,.04,.12,.42,rng=rng);y=np.roll(x,15)
    elif name=="vinyl_crackle":
        x=.013*noise(rng,n,200,13000);y=.013*noise(rng,n,200,13000)
        for k in range(200):
            at=rng.uniform(0,len(t)-.08);a=pulse(n,at,.016,rng.uniform(.02,.09),rng=rng)
            if k%2:x+=a
            else:y+=a
    elif name=="bass_impact":
        f=82*np.exp(-t*1.4)+36;x=.42*tone(n,f)*np.exp(-t*1.5)
        x+=pulse(n,.03,.15,.08,rng=rng);y=x.copy()
    elif name=="footsteps":
        for k in range(6):
            a=pulse(n,.12+k*.43,.18,.18,rng=rng)
            if k%2:x+=a
            else:y+=a
    env=np.minimum(1,np.arange(n)/max(1,int(.009*SR)))
    env*=np.minimum(1,np.arange(n)[::-1]/max(1,int(.012*SR)))
    wave=np.column_stack((x,y))*env[:,None]
    peak=np.max(np.abs(wave))
    if peak>0:wave=wave*(.73/max(.73,peak))
    return wave.astype("float32")
def install():
    DEST.mkdir(parents=True,exist_ok=True)
    made=[]
    for name in NAMES:
        p=DEST/(name+".wav")
        if not p.is_file():
            sf.write(p,make(name),SR,subtype="PCM_24");made.append(name)
    manifest=DEST/"sfx-provenance.json"
    if not manifest.exists():
        manifest.write_text(json.dumps({"creator":"Music Studio procedural synthesis", "license":"Original, generated locally; no third-party source samples", "status":"Foley-style approximations, not field recordings", "sample_rate":SR,"names":NAMES},indent=2),encoding="utf-8")
    return made
if __name__=="__main__":
    made=install()
    print("SFX pack: "+str(len(NAMES))+" files, newly created "+str(len(made)))

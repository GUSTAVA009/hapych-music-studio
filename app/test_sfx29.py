import json,sys
from pathlib import Path
import numpy as np
import soundfile as sf
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
from studio_sections import compile_sections
from sound_effects29 import planned_effects,render_effects
sfx=["Heavy rain on asphalt","Distant police siren","Car unlock beep, door opens, engine starts",
"Radio static, station tuning","Phone ringing","Cards shuffling","Bass-heavy car stereo",
"Phone vibration","Lighter click","Slow clock ticking","Car engine rev",
"Distant police radio chatter","Tires rolling through rain","Wind passing car windows",
"Coins dropping on table","Cards slapped on table","Hookah bubbling",
"Alarm clock ringing","Alarm clock stops","Rain fades","Car engine shuts off","Tape Click"]
raw="[Intro - Dark Cinematic Piano, Low Strings]\n"+ "\n".join("[SFX: "+s+"]" for s in sfx[:7])+"\nНовый день, тот же город\n[Verse 1 - Deep Rap]\n"+"\n".join("[SFX: "+s+"]" for s in sfx[7:16])+"\nСнова вечер, снова движ\n[Outro - Fading Saxophone, Vinyl Crackle]\n"+"\n".join("[SFX: "+s+"]" for s in sfx[16:])+"\nОпять день сурка"
prepared=compile_sections(raw);prepared["raw_lyrics"]=raw
plans=planned_effects(prepared["sections"])
print("plan effects",len(plans),"supported",sum(x["supported"] for x in plans))
assert sum(x["supported"] for x in plans)>=23, [(x["requested"],x["supported"]) for x in plans]
assert not any("[SFX:" in sec["lyrics"] for sec in prepared["sections"])
folder=Path.home()/"Music Studio"/"Diagnostics"/"SFX29";folder.mkdir(parents=True,exist_ok=True)
sr=48000;t=np.arange(sr*50)/sr
source=folder/"test_source.wav";master=folder/"test_master.wav";stem=folder/"test_fx.wav"
sound=np.column_stack((np.sin(t*2*np.pi*180),np.sin(t*2*np.pi*190)))*.045
sf.write(source,sound,sr,subtype="PCM_24")
report=render_effects(source,master,prepared,"",stem)
a,s=sf.read(master)
fx,_=sf.read(stem)
assert s==48000 and a.ndim==2 and len(a)==len(sound)
assert np.all(np.isfinite(a))
assert .001<float(np.max(np.abs(fx)))<.95
assert float(np.max(np.abs(a)))<.95
assert report["effects_requested"]>=23 and len(report["effects_applied"])>=23
(folder/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASS rendered",len(report["effects_applied"]),"SFX, peak",report["peak_dbfs"],"dBFS")
print("FX stem",stem)

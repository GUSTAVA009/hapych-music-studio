"""SFX high-fidelity regression and catalog test for Music Studio."""
import sys
from pathlib import Path
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
from sound_quality32 import scan,preferred_path,recognize
from sound_catalog30 import stats,match
from sound_effects29 import planned_effects,canonical,_asset_path
from studio_sections import compile_sections
q=scan();s=stats()
assert q["recorded"]==161 and q["high_fidelity_count"]==161
assert s["total_imported_audio"]>=1400,(s["total_imported_audio"],s["mapped_categories"])
print("IMPORTS",s["total_imported_audio"],"FIELD_RECORDINGS",q["recorded"],"HI_FIDELITY",q["high_fidelity_count"])
tests=[
 ("[SFX: Phone ringing]","phone_ring","Phonering-otherend.wav"),
 ("[SFX: Phone vibration]","phone_vibrate","Phone_vibrate.wav"),
 ("[SFX: Clock ticking]","clock_tick","loopable-ticking-clock.wav"),
 ("[SFX: Human laughter]","human_laughter","laugh1.wav"),
 ("[SFX: Male breathing]","male_breath","breath-male.wav"),
 ("[SFX: Shuffling paper]","paper_shuffle",None),
 ("[SFX: Finger snap]","finger_snap","click-finger-snap.wav"),
 ("[SFX: Night crickets ambience]","night_ambience","night-crickets-ambience-on-rural-property.wav"),
 ("[SFX: Cough]","human_cough",None),
 ("[SFX: Glass breaking]","glass_break",None),
 ("[SFX: Heavy rain on asphalt]","rain_asphalt",None),
 ("[SFX: Car engine starts]","engine_start","car_engine_start.wav"),
]
raw="[Intro]\n"+"\n".join(x[0] for x in tests)+"\nНовый день"
sections=compile_sections(raw)["sections"]
plans=planned_effects(sections)
assert len(plans)>=len(tests),(len(plans),len(tests))
for i,(cue,key,file) in enumerate(tests):
 found=plans[i]
 path=_asset_path(found["effect"])
 print(key,"=>",found["effect"],found["supported"],str(path.name))
 assert found["effect"]==key,(cue,found)
 assert found["supported"],cue
 if file:assert path.name.lower()==file.lower()
print("NEW_SFX_LIBRARY_OK")

import sys
from pathlib import Path
APP=Path(__file__).resolve().parent;sys.path.insert(0,str(APP))
from sound_catalog30 import stats,match,asset
from studio_sections import compile_sections
from sound_effects29 import planned_effects
s=stats()
print("STATS",s["total_imported_audio"],"distinct filenames",s["searchable_specific_samples"],"mapped categories",s["mapped_categories"])
cases=[
("Thunderstorm","thunder"),("Heavy city traffic","city_traffic"),
("Wet footsteps on wet asphalt","wet_footsteps"),
("Camera shutter clicking","camera_shutter"),("Phone Ring SFX","phone_ring"),
("Low laughter and muffled room chatter","room_laughter_chatter"),
("Door lock key clicks","door_lock"),("Radio static hiss","radio_noise"),
("Coins dropping on table","coins_drop"),("Wind passing car windows","wind_car"),
("Vinyl crackle","vinyl_crackle"),("Opening wooden door","door_open"),
("Cards shuffling","cards_shuffle"),("Glass breaking","glass_break"),
("Cigarette lighter click","cigarette_lighter"),("Police siren","police_siren")
]
text="[Intro]\n"+"\n".join("[SFX: "+c+"]" for c,_ in cases)+"\nНаш город\n"
sections=compile_sections(text)["sections"]
planned=planned_effects(sections)
for (cue,expect),result in zip(cases,planned):
 print(cue,"=>",result["effect"],result["supported"])
 assert result["supported"],cue
 assert result["effect"]==expect,(cue,result["effect"],expect)
assert s["total_imported_audio"]>=1200
assert s["mapped_categories"]>=40
print("CATALOG_INTEGRATION_OK")

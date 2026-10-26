from pathlib import Path
import json,sys
ROOT=Path.home()/"Music Studio";APP=ROOT/"app";sys.path.insert(0,str(APP))
from studio_sections import prepare_request
from sound_effects29 import render_effects
songs=list((ROOT/"Мои треки").glob("*QA33*.track.json"))
assert len(songs)==1
meta=json.loads(songs[0].read_text(encoding="utf-8"))
sources=list((ROOT/"Исходные версии").glob(songs[0].stem.replace(".track","")+".wav"))
if not sources:
 sources=list((ROOT/"Исходные версии").glob("*QA33*.wav"))
assert sources, "Original generation must exist; do not remix output recursively."
p=prepare_request({"style":meta["style_original"],"lyrics":meta["lyrics_original"]})
dest=ROOT/"Diagnostics"/"AUTO_QA33"
result=render_effects(sources[0],dest/"quality33_scene_mix.wav",p,"",dest/"quality33_scene_fx.wav")
(dest/"quality33_scene_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
rain=[x for x in result["effects_applied"] if x["effect"]=="rain_asphalt"]
assert rain and rain[0]["rendered_seconds"]>=4.0,rain
assert not result["effects_missing"]
print("SCENE_MIX_QA_OK",len(result["effects_applied"]),"RAIN_S",rain[0]["rendered_seconds"],"PEAK_DBFS",result["peak_dbfs"],"OUTPUT",dest/"quality33_scene_mix.wav")

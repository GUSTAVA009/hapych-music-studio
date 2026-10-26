from pathlib import Path
import json,sys,soundfile as sf,numpy as np
R=Path.home()/"Music Studio";sys.path.insert(0,str(R/"app"))
from studio_sections import prepare_request
from sound_effects29 import render_effects,planned_effects
from sound_arranger35 import bpm_from,arrange_event
files=list((R/"Мои треки").glob("*QA34*.track.json"))
assert len(files)==1
meta=json.loads(files[0].read_text(encoding="utf-8"))
sources=list((R/"Исходные версии").glob("*QA34*.wav"))
assert len(sources)==1
request={"style":meta.get("style_original",""),"lyrics":meta.get("lyrics_original",""),
         "bpm":92,"duration":65}
prepared=prepare_request(request)
print("BPM",bpm_from(prepared))
print("SECTIONS",[(x["section"],x["id"]) for x in prepared["sections"]])
print("PLANS",[(x["requested"],x["effect"],x["supported"]) for x in planned_effects(prepared["sections"])])
assert bpm_from(prepared)==92
dir=R/"Diagnostics"/"QA35";dir.mkdir(parents=True,exist_ok=True)
out=dir/"QA35_Gorodskie_ogni_sfx_new.wav";stem=dir/"QA35_Gorodskie_ogni_sfx_only.wav"
report=render_effects(sources[0],out,prepared,"",stem)
(dir/"QA35_Gorodskie_ogni_sfx_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("APPLIED",json.dumps(report["effects_applied"],ensure_ascii=True)[:6000])
print("MISSING",report["effects_missing"],"WARN",report["warnings"],"PEAK",report["peak_dbfs"])
rain=[x for x in report["effects_applied"] if x["effect"]=="rain_asphalt"]
assert rain and rain[0]["rendered_seconds"]>=12.5,rain
assert rain[0]["start"]==0 and rain[0]["timing_basis"]=="bpm_bar_grid_intro_environment"
assert rain[0]["enabled"]==True
assert not report["effects_missing"]
assert out.is_file()
print("QA35_MUSIC_FOLLOW_SFX_TEST_PASS",out)

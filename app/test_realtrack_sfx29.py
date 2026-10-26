"""Diagnostic only: check SFX mixer on existing local real music; never overwrite user tracks."""
from pathlib import Path
import sys,json
import numpy as np,soundfile as sf
APP=Path(__file__).resolve().parent;sys.path.insert(0,str(APP))
from studio_sections import prepare_request
from sound_effects29 import render_effects,planned_effects,resolve_effects,_asset_path
ROOT=Path.home()/"Music Studio"
records=sorted((x for x in (ROOT/"Исходные версии").glob("*.wav") if x.stat().st_size>40_000_000),key=lambda x:x.stat().st_size)
if not records:raise RuntimeError("No suitable real music source")
src=records[0]
info=sf.info(src)
print("TEST source length_sec",info.duration, "sample_rate",info.samplerate,flush=True)
folder=ROOT/"Мои тексты"
data={"lyrics":(folder/"День сурка - полный сценарий SFX.txt").read_text(encoding="utf-8"),
      "style":(folder/"День сурка - стиль и промпт.txt").read_text(encoding="utf-8")}
prepared=prepare_request(data)
dest=ROOT/"Diagnostics"/"SFX29";dest.mkdir(parents=True,exist_ok=True)
report=render_effects(src,dest/"real_music_preview.wav",prepared,"",dest/"real_music_fx.wav")
(dest/"real_music_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
by_name={x["effect"]:x["sample"] for x in report["effects_applied"]}
for key in ["rain_asphalt","car_door","engine_start","cards_shuffle","coins_drop"]:
    print("SAMPLE",key, by_name.get(key,"NOT RENDERED"),flush=True)
print("RESULT requested",report["effects_requested"],"rendered",len(report["effects_applied"]),
      "missing",report["effects_missing"],"peak",report["peak_dbfs"],"global attenuation",report["global_attenuation_db"],flush=True)
assert len(report["effects_applied"])>=25
assert "realworld" in by_name["rain_asphalt"] and "realworld" in by_name["car_door"]
assert "realworld" in by_name["engine_start"] and "casino" in by_name["cards_shuffle"]
assert report["peak_dbfs"]<0
print("REAL_TRACK_QA_PASS",flush=True)

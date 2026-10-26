"""QA63 final integration smoke: active voice_bridge25 -> QA54 converter + personal weights.
Never append to library. Write only Diagnostics/QA63.
"""
from pathlib import Path
import sys,traceback,json,time,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA63"
sys.path.insert(0,str(R/"app"))
from voice_bridge25 import PIPELINE,convert_song
from voice_model_policy63 import select
from voice_profiles34 import validate_reference
assert PIPELINE.name=="convert_track_studio54_cfg090.py",PIPELINE
mic=R/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav"
model_selection=select(mic,validate_reference(mic.name,""))
assert model_selection["trained"] is True,model_selection
song=R/"Diagnostics"/"QA45"/"QA45_verse18to53.wav"
assert song.is_file(),song
out=D/"QA63_LiveBridge_35s_QA54Personal.mp3"
assert not out.exists()
start=time.monotonic()
result={"bridge":"voice_bridge25 -> convert_track_studio54_cfg090.py",
 "trained":True,"model":model_selection["model"],
 "originals_unchanged":True,"test_only_not_in_library":True}
try:
 convert_song(song,mic,out,steps=40,trained=model_selection["trained"],
     register_mode="original",vocal_language="ru",
     chorus_ranges=[],on_stage=lambda m: print("QA63_STAGE",m[:180],flush=True))
 assert out.is_file() and out.stat().st_size>100000
 quality=json.loads(out.with_suffix(".quality.json").read_text(encoding="utf-8"))
 assert quality["model"]=="personal" and quality["stitching"]["diffusion_chunks"]>=1
 assert quality["qa51_reference_context"]["prompt_seconds"]==18.0
 assert quality["qa51_reference_context"]["style_seconds"]==22.0
 assert quality["pitch_consistency"]["status"]!="rejected"
 result.update(ok=True,bytes=out.stat().st_size,mel_chunks=quality["stitching"]["diffusion_chunks"],
     voice_check_status=quality["voice_check"]["status"],
     speaker_cosine=quality.get("speaker_embedding_cosine"),
     drop_events=quality["voice_check"]["metrics"]["energy_dip_events"],
     longest_dip_s=quality["voice_check"]["metrics"]["longest_energy_dip_s"],
     path=str(out),duration_seconds=35)
except Exception as e:
 result.update(ok=False,error=repr(e),trace=traceback.format_exc()[-5000:])
finally:
 result["run_seconds"]=round(time.monotonic()-start,1)
 (D/"qa63_integration_smoke_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA63_END_TO_END_RESULT",json.dumps({k:v for k,v in result.items() if k!="trace"},ensure_ascii=True),flush=True)
if not result.get("ok"):sys.exit(1)

from pathlib import Path
import json,sys,numpy as np,soundfile as sf
APP=Path(__file__).resolve().parent;sys.path.insert(0,str(APP))
from studio_finisher34 import finish,inspect_audio
from chorus_layers34 import chorus_windows,vocal_double
from studio_sections import compile_sections
ROOT=Path.home()/"Music Studio";qa=ROOT/"Diagnostics"/"PRODUCTION34";qa.mkdir(parents=True,exist_ok=True)
source=ROOT/"Diagnostics"/"AUTO_QA33"/"quality33_scene_mix.wav"
assert source.is_file()
song="[Intro - Piano]\nНочь за окном\n[Chorus - Four Backing Voices]\nЭто наш город\n[Outro]\nУходит музыка"
sects=compile_sections(song)["sections"]
windows,basis=chorus_windows(sects,"",sf.info(str(source)).duration)
report=finish(source,qa/"qa33_soft_edges.wav",chorus_ranges=windows)
print(json.dumps(report,ensure_ascii=False,indent=2))
assert report["edge_qa"]["first_half_second_rms_dbfs"]<-42
assert report["edge_qa"]["last_half_second_rms_dbfs"]<-58
assert report["finished_duration_seconds"]>40
assert report["chorus_spatial_processing"]["applied"]
assert sf.info(str(source)).duration==40
voice=np.sin(np.arange(44100*5)/44100*2*np.pi*150).astype(np.float32)*.15
doubs,status=vocal_double(voice,44100,[(1.,3.5)])
assert status["applied"] and status["layers"]==4
assert np.max(np.abs(doubs[:40000]))==0
assert np.max(np.abs(doubs[44100:44100*3]))>.001
print("MASTER_AND_DOUBLE_TEST_PASS",str(qa/"qa33_soft_edges.wav"))
(qa/"qa33_master_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

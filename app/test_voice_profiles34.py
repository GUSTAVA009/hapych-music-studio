"""Isolated automated tests; never writes artist profiles to the user's database."""
from pathlib import Path
import tempfile,sys,json
import numpy as np
import soundfile as sf
ROOT=Path.home()/"Music Studio";APP=ROOT/"app";sys.path.insert(0,str(APP))
import voice_profiles34 as v
with tempfile.TemporaryDirectory() as d:
 temp=Path(d)
 v.DB=temp/"profiles.json";v.VOICES=temp/"voices";v.VOICES.mkdir()
 sample=v.VOICES/"singer_a.wav";sample2=v.VOICES/"singer_b.wav"
 wave=np.sin(np.arange(44100*3)/44100*np.pi*2*150).astype("float32")*.08
 sf.write(str(sample),wave,44100)
 sf.write(str(sample2),wave,44100)
 a=v.create_profile("Исполнитель А",True,"ru")
 b=v.create_profile("Исполнитель Б",True,"en")
 assert a["id"]!=b["id"]
 assert v.list_profiles()["unassigned_recordings"]==2
 v.assign(sample.name,a["id"],True,folder=v.VOICES)
 v.assign(sample2.name,b["id"],True,folder=v.VOICES)
 assert v.validate_reference(sample.name,a["id"])["matched"]
 assert v.validate_reference(sample2.name,b["id"])["matched"]
 try:v.validate_reference(sample.name,b["id"]);raise AssertionError("Cross-artist validation failed")
 except ValueError:pass
 try:v.assign(sample.name,b["id"],True,folder=v.VOICES);raise AssertionError("Cross assignment allowed")
 except ValueError:pass
 try:v.create_profile("Unauthorized",False);raise AssertionError("Permission absent")
 except ValueError:pass
 assert not v.list_profiles()["unassigned_recordings"]
 print("VOICE_PROFILES_34_TEST_PASSED")

import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from studio_mix21 import finish
sr=44100
duration=8
n=sr*duration
t=np.arange(n)/sr
# Speech-like pitched vowel with intermittent voiced passages and consonant-band noise
speech=(.12*np.sin(2*np.pi*140*t)+.035*np.sin(2*np.pi*280*t)).astype("float32")
active=np.where((t%1.5)<1.0,1.,.01).astype("float32")
speech*=active
rng=np.random.default_rng(1)
sibilance=np.zeros(n,np.float32)
for start in (2.1,4.6,6.4):
 mask=(t>start)&(t<start+.2)
 sibilance[mask]=rng.normal(0,.07,mask.sum())
voice=speech+sibilance
instrument=np.stack([.12*np.sin(2*np.pi*90*t)+.06*np.sin(2*np.pi*190*t),
    .12*np.sin(2*np.pi*90*t)+.06*np.sin(2*np.pi*195*t)],axis=1).astype("float32")
with tempfile.TemporaryDirectory() as root:
 root=Path(root)
 sf.write(root/"v.wav",voice,sr)
 sf.write(root/"r.wav",voice*.8,sr)
 sf.write(root/"b.wav",instrument,sr)
 report=finish(root/"v.wav",root/"b.wav",root/"r.wav",root/"processed.wav",root/"mixed.wav",sr=sr)
 result,_=sf.read(root/"mixed.wav",always_2d=True)
 assert len(result)==n
 assert np.all(np.isfinite(result))
 assert np.max(np.abs(result))<.92
 assert 0<=report["deesser"]["max_reduction_db"]<=1.81
 assert report["source_vocal_blended"]==False
 assert report["phoneme_reconstruction_performed"]==False
 assert not np.allclose(result[:,0],result[:,1])
 print("VOCAL_MIX_21_OK",report)

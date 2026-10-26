"""QA83 isolate original ACE lead for comparison and SoulX reprocessing.
Does not overwrite generated songs or existing voice models.
"""
from pathlib import Path
import sys,subprocess,json,time,os
R=Path.home()/'Music Studio';W=R/'Diagnostics'/'QA83-CurrentTracks';W.mkdir(parents=True,exist_ok=True)
engine=R/'Voice Engine';exe=engine/'.venv'/'Scripts'/'python.exe'
job='20261025_151141_91ce16_'
all_files=sorted([p for p in (R/'Исходные версии').glob(job+'*.wav') if p.name.endswith(('_1.wav','_2.wav'))])
assert len(all_files)==2,[(p.name,p.stat().st_size) for p in all_files]
outputs={}
for original in all_files:
  tag='take1' if original.name.endswith('_1.wav') else 'take2'
  dest=W/tag/'stems';dest.mkdir(parents=True,exist_ok=True)
  vocal=dest/'htdemucs'/original.stem/'vocals.wav'
  backing=dest/'htdemucs'/original.stem/'no_vocals.wav'
  if not (vocal.is_file() and backing.is_file()):
    print('DEMUX_BEGIN',tag,original.stat().st_size,flush=True)
    command=[str(exe),'-m','demucs','-n','htdemucs','--two-stems=vocals',
      '-d','cuda','--segment','7','-o',str(dest),str(original)]
    with (W/(tag+'_demucs.log')).open('w',encoding='utf-8') as log:
      p=subprocess.run(command,cwd=str(engine),stdout=log,stderr=subprocess.STDOUT,
      timeout=1200)
    if p.returncode:raise RuntimeError(tag+' failed demucs: '+(W/(tag+'_demucs.log')).read_text(encoding='utf-8',errors='replace')[-1200:])
  assert vocal.stat().st_size>1000000 and backing.stat().st_size>1000000
  outputs[tag]={'input':str(original),'vocals':str(vocal),'backing':str(backing),
    'vocal_bytes':vocal.stat().st_size,'backing_bytes':backing.stat().st_size}
  print('DEMUX_READY',tag,json.dumps(outputs[tag],ensure_ascii=True),flush=True)
(W/'qa83_demucs_manifest.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')
print('DEMUX_BOTH_COMPLETE',flush=True)

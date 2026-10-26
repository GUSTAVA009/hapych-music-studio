"""Prepare personal dry microphone voice takes for Seed-VC fine-tuning.
No generated tracks or commercial recordings are included.
"""
from pathlib import Path
import subprocess,json
root=Path.home()/'Music Studio'
src=root/'Мой голос'
out=root/'Voice Engine'/'training_dataset'/'OWNER_VOICE'
out.mkdir(parents=True,exist_ok=True)
results=[]
for i,p in enumerate(sorted(src.glob('*.m4a')),1):
 target=out/('alex_voice_%02d.wav'%i)
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(p),
      '-map','0:a:0','-ac','1','-ar','44100','-c:a','pcm_s16le',str(target)]
 subprocess.run(cmd,check=True,timeout=60)
 prob=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(target)],
     capture_output=True,text=True,timeout=30,check=True)
 sec=float(prob.stdout.strip())
 if not 1<=sec<=30:
  target.unlink(missing_ok=True)
  raise ValueError(f'Train sample must be 1..30s: {p.name}: {sec}')
 results.append({'source':p.name,'processed':str(target),'seconds':sec})
(out/'dataset_manifest.json').write_text(json.dumps({'purpose':'personal seed-vc voice fine-tuning','samples':results},ensure_ascii=False,indent=2),encoding='utf-8')
print('DATASET_PREPARED',json.dumps(results,ensure_ascii=False),flush=True)

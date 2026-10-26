from pathlib import Path
import subprocess,json
root=Path.home()/'Music Studio'/'Voice Engine'/'training_dataset'
src=root/'ALEX_KZNT'
dst=root/'ALEX_KZNT_SHORT'
dst.mkdir(parents=True,exist_ok=True)
parts=[]
for wav in sorted(src.glob('alex_voice_*.wav')):
 if wav.name.startswith('alex_voice_01'):
  spans=[(0,8.0)]
 else:
  spans=[(0,7.3),(7.4,7.3),(14.8,7.3)]
 for n,(at,duration) in enumerate(spans,1):
  out=dst/(f'{wav.stem}_part{n:02d}.wav')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(at),'-t',str(duration),'-i',str(wav),
      '-ac','1','-ar','44100','-c:a','pcm_s16le',str(out)],check=True,timeout=30)
  parts.append(str(out))
print('SHORT_VOICE_DATASET',json.dumps(parts,ensure_ascii=True),flush=True)

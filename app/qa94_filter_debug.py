from pathlib import Path
import subprocess,re,numpy as np,soundfile as sf
r=Path.home()/'Music Studio'/'Diagnostics'/'QA94-IntonationPreview'
src=r/'sine440.wav';out=r/'sine_commands.wav'
sr=44100
for target in ['rb','rubberband','rubberband@rb','Parsed_rubberband_1']:
 af=f"asendcmd=c='1.3 {target} pitch 1.06',rubberband@rb=pitch=1:formant=preserved"
 proc=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','debug','-y','-i',str(src),'-af',af,'-c:a','pcm_f32le',str(out)],capture_output=True,text=True,timeout=30)
 logs=[x for x in proc.stderr.splitlines() if any(t in x.lower() for t in ('command', 'target', 'ret:', 'not implemented','error parsing'))][-8:]
 if proc.returncode:
  print('TARGET',target,'ERROR',logs,flush=True);continue
 y,s=sf.read(out,dtype='float32')
 def peak(a):
  a=a*np.hanning(len(a))
  ff=np.abs(np.fft.rfft(a,n=sr*2));ix=np.argmax(ff)
  return round(ix*.5,3)
 print('TARGET',target,'FREQS',[peak(y[int(t*sr):int((t+.5)*sr)]) for t in (.4,2.1,3.2)],'CMD_LOG',logs,flush=True)

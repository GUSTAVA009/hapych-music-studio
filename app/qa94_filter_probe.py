"""QA94: verify FFmpeg supports continuous dynamic pitch commands on Windows.
This probe uses ONLY a synthetic sine wave, not user audio.
"""
from pathlib import Path
import numpy as np,soundfile as sf,subprocess
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA94-IntonationPreview'
D.mkdir(parents=True,exist_ok=True)
sr=44100; t=np.arange(sr*4)/sr
x=(.23*np.sin(2*np.pi*440*t)).astype('float32')
src=D/'sine440.wav';out=D/'sine_commands.wav'
sf.write(src,x,sr)
filters=[
 "asendcmd=c='1.3 rb pitch 1.06',rubberband@rb=tempo=1:pitch=1:formant=preserved:transients=smooth",
 "asendcmd=c='1.3 rb pitch 1.06',rubberband@rb=tempo=1:pitch=1",
]
def freq(y):
 samples=y[:min(len(y),round(.7*sr))]
 fft=np.abs(np.fft.rfft(samples*np.hanning(len(samples)),n=sr*2))
 k=np.argmax(fft)
 return float(np.fft.rfftfreq(sr*2,1/sr)[k])
for af in filters:
 cmd=['ffmpeg','-nostdin','-hide_banner','-v','info','-y','-i',str(src),'-af',af,'-c:a','pcm_f32le',str(out)]
 z=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
 print('FILTER_ATTEMPT',af,'RETURNCODE',z.returncode,'LOG_TAIL',z.stderr[-1200:].encode('unicode_escape').decode(),flush=True)
 if not z.returncode and out.exists():
  y,s=sf.read(out,dtype='float32')
  before=freq(y[int(.25*sr):int(1.1*sr)])
  after=freq(y[int(2.0*sr):int(3.3*sr)])
  print('MEASURED_FREQUENCIES',before,after,'ratio',after/before,'audio_seconds',len(y)/s,flush=True)
  if 437<before<443 and 465<after<469:
   print('QA94_DYNAMIC_RUBBERBAND_PROBE_PASS')
   break
else:raise RuntimeError('No supported dynamic pitch command filter')

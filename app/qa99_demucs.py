from pathlib import Path
import subprocess,sys,os
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA99-LowRegister'
src=D/'qa99_lowbaritone_35s.wav';dst=D/'low_stems'
assert src.is_file()
exe=R/'Voice Engine'/'.venv'/'Scripts'/'python.exe'
cmd=[str(exe),'-m','demucs','-n','htdemucs','--two-stems=vocals',
      '-o',str(dst),str(src)]
os.environ['HF_HUB_OFFLINE']='1'
with (D/'qa99_demucs.log').open('w',encoding='utf8') as f:
 p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,
                  timeout=240,stdin=subprocess.DEVNULL)
print('QA99_DEMUCS_EXIT',p.returncode,flush=True)
stem=dst/'htdemucs'/'qa99_lowbaritone_35s'/'vocals.wav'
assert p.returncode==0 and stem.is_file()
print('QA99_VOCALS_READY',stem.stat().st_size,flush=True)

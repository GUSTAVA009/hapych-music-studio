"""Cached local pitch hint; never changes text or infers a person's identity/gender."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent.parent;CACHE=R/'app'/'voice_profiles';CACHE.mkdir(exist_ok=True)
def profile(reference):
 p=Path(reference);key=hashlib.sha256((str(p.resolve())+':'+str(p.stat().st_size)+':'+str(p.stat().st_mtime_ns)).encode()).hexdigest()[:24]
 out=CACHE/(key+'.json')
 if out.is_file():return json.loads(out.read_text(encoding='utf-8'))
 command=[str(R/'Voice Engine'/'.venv'/'Scripts'/'python.exe'),str(R/'Voice Engine'/'reference_profile16.py'),'--reference',str(p),'--output',str(out)]
 proc=subprocess.run(command,capture_output=True,timeout=50,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 if proc.returncode or not out.is_file():return {'reliable':False,'warning':'Диапазон записи не измерен; высота из музыкального задания сохранена.'}
 return json.loads(out.read_text(encoding='utf-8'))

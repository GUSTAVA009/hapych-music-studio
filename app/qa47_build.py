"""QA47 expose raw converter stem in diagnostic-only fork.
Leaves original voice converters and master unchanged.
"""
from pathlib import Path
import py_compile
V=Path.home()/"Music Studio"/"Voice Engine"
src=V/"convert_track_studio44.py"
text=src.read_text(encoding="utf-8")
before="            shutil.copy2(work/'vocal_finished.wav',output.with_suffix('.finished.wav'))"
after="            shutil.copy2(original_converted,output.with_suffix('.raw.wav'))\n"+before
assert text.count(before)==1
new=V/"convert_track_studio47.py"
new.write_text(text.replace(before,after),encoding="utf-8")
py_compile.compile(str(new),doraise=True)
print("QA47_RAW_DIAGNOSTIC_FORK",new)

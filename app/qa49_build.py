from pathlib import Path
import py_compile
r=Path.home()/"Music Studio"/"Voice Engine"
s=(r/"seed-vc"/"inference_studio17.py").read_text(encoding="utf-8")
old="    overlap_frames = 72"
assert s.count(old)==1
s=s.replace(old,"    overlap_frames = 128")
(r/"seed-vc"/"inference_studio49.py").write_text(s,encoding="utf-8")
c=(r/"convert_track_studio48.py").read_text(encoding="utf-8")
assert c.count("inference_studio17.py")==1
c=c.replace("inference_studio17.py","inference_studio49.py")
(r/"convert_track_studio49.py").write_text(c,encoding="utf-8")
py_compile.compile(str(r/"seed-vc"/"inference_studio49.py"),doraise=True)
py_compile.compile(str(r/"convert_track_studio49.py"),doraise=True)
print("QA49_SAFE_FORK_READY")
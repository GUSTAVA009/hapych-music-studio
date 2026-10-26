from pathlib import Path
import py_compile
r=Path.home()/"Music Studio"/"Voice Engine"
s=(r/"voice_continuity42.py").read_text(encoding="utf-8")
changes={
"weight=gaussian_filter1d(candidates.astype(float),sigma=2.0)":"weight=gaussian_filter1d(candidates.astype(float),sigma=6.0)",
"boost=np.clip((local-4)/10,0,1)":"boost=np.clip((local-5)/13,0,1)",
"boost=gaussian_filter1d(boost,sigma=2.0)":"boost=gaussian_filter1d(boost,sigma=6.0)",
"    gain_db=6.5*np.minimum(boost,weight)":"    gain_db=np.clip(2.6*np.minimum(boost,weight),0,2.6)\n    for i in range(1,len(gain_db)):\n        gain_db[i]=min(gain_db[i],gain_db[i-1]+0.11)\n    for i in range(len(gain_db)-2,-1,-1):\n        gain_db[i]=min(gain_db[i],gain_db[i+1]+0.11)",
'"boost_ceiling_db":6.5':'"boost_ceiling_db":2.6',
}
for a,b in changes.items():
 assert s.count(a)==1,a
 s=s.replace(a,b)
(r/"voice_continuity48.py").write_text(s,encoding="utf-8")
py_compile.compile(str(r/"voice_continuity48.py"),doraise=True)
c=(r/"convert_track_studio44.py").read_text(encoding="utf-8")
assert c.count("from voice_continuity42 import repair")==1
c=c.replace("from voice_continuity42 import repair","from voice_continuity48 import repair")
(r/"convert_track_studio48.py").write_text(c,encoding="utf-8")
py_compile.compile(str(r/"convert_track_studio48.py"),doraise=True)
print("QA48_FORK_OK")

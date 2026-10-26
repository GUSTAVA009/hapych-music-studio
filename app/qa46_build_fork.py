"""Build two experimental QA46 forks without modifying Music Studio production."""
from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
V=R/"Voice Engine"
old=V/"studio_mix21.py";new=V/"studio_mix46.py"
x=old.read_text(encoding="utf-8")
edits=[
  ("amount*1.8","amount*1.15"),
  ("((0,17,.065),(1,31,.070),(0,47,.035),(1,64,.035))",
   "((0,19,.032),(1,37,.034),(0,61,.016),(1,83,.015))"),
  ("side=side+side_high*.18","side=side+side_high*.12"),
  ("\"backing_stereo_width\":1.18","\"backing_stereo_width\":1.12"),
  ("\"method\":\"source_level_constant_gain_spacious21\"",
   "\"method\":\"source_level_constant_gain_soft_room46\""),
  ("\"stereo_depth\":\"direct center lead, low-level asymmetric early reflections 17-64ms\"",
   "\"stereo_depth\":\"direct center lead, restrained early reflections 19-83ms\""),
]
for before,after in edits:
 count=x.count(before)
 assert count==1,(before,count)
 x=x.replace(before,after)
new.write_text(x,encoding="utf-8")
py_compile.compile(str(new),doraise=True)
conv=V/"convert_track_studio44.py"
out=V/"convert_track_studio46.py"
s=conv.read_text(encoding="utf-8")
assert s.count("from studio_mix21 import finish")==1
assert s.count("from voice_continuity42 import repair")==1
s=s.replace("from studio_mix21 import finish","from studio_mix46 import finish")
s=s.replace("from voice_continuity42 import repair","from voice_continuity46 import repair")
s=s.replace("voice_guard42_continuity42_pitch_clean51_stereo_mix21",
            "voice_guard42_continuity46_pitch_clean51_stereo_mix46")
out.write_text(s,encoding="utf-8")
py_compile.compile(str(out),doraise=True)
py_compile.compile(str(V/"voice_continuity46.py"),doraise=True)
print("QA46_EXPERIMENTAL_MODULES_VERIFIED",new,out,flush=True)

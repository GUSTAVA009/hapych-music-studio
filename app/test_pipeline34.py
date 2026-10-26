"""Production34 integration checks; no full GPU generation."""
import json,sys
from pathlib import Path
R=Path.home()/"Music Studio";APP=R/"app";sys.path.insert(0,str(APP))
from song_structure34 import condition
from studio_sections import compile_sections
from chorus_layers34 import chorus_windows
from sound_effects29 import planned_effects
import studio_server
raw="[Intro - Soft Piano]\nМой город просыпается\n[Chorus - Four Male Backing Voices]\nРодной мой город, я вернусь\n[Verse 1 - Male Rap]\nЯ начинаю всё сначала\n[Outro - Slow Piano]\nМой город уснул"
style="Deep male Russian rap, four male backing voices, 92 BPM, D minor, soft piano"
prepared=studio_server.prepare_request({"lyrics":raw,"style":style,"duration":40,"bpm":92,"vocal_language":"auto","two_versions":False})
print("ARRANGEMENT:",prepared["structure_plan"])
print("LYRICS_START:",prepared["lyrics"][:190])
print("LYRICS_END:",prepared["lyrics"][-180:])
assert prepared["structure_plan"]["prelude_added"]
assert prepared["structure_plan"]["coda_added"]
assert len(prepared["lyrics"])<=4096
assert all(x in prepared["lyrics"] for x in ["Мой город просыпается","Родной мой город, я вернусь","Я начинаю всё сначала","Мой город уснул"])
assert prepared["style_plan"].get("prompt_compiler")=="loss_aware_style30"
windows,basis=chorus_windows(prepared["sections"],"",40)
print("CHORUS_WINDOWS",windows,basis)
assert len(windows)==1 and windows[0][1]>windows[0][0]
instr=studio_server.prepare_request({"lyrics":"[Instrumental]","style":style,"duration":40,"instrumental":True})
assert instr["lyrics"]=="[Instrumental]"
print("PIPELINE34_ARRANGEMENT_INTEGRATION_PASS")

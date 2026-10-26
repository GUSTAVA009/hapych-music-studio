"""QA74 read-only regression for reference register in ACE caption."""
from pathlib import Path
import json,sys
ROOT=Path.home()/"Music Studio"
sys.path.insert(0,str(ROOT/"app"))
from voice_caption74 import integrate
request=json.loads((ROOT/"app"/"requests"/"8ea4e8e830e4453d99204c7ea93203dd.json").read_text(encoding="utf-8"))
caption=request["preparation"]["caption"]
profile=request["preparation"]["reference_profile"]
assert len(caption)==508,(len(caption),caption)
assert profile["reliable"],profile
assert abs(profile["median_hz"]-119.76)<.1
result=integrate(caption,profile)
assert result["status"]=="integrated",result
assert len(result["caption"])<=512
assert "low male baritone" in result["caption"].lower()
assert result["reference_hint_sent_to_model"]
for essential in ("92 BPM","F# minor","piano","electric guitar","808","native Russian diction","connected melodic singing","smooth register transitions"):
    assert essential.lower() in result["caption"].lower(),essential
assert "low male baritone" in integrate(result["caption"],profile)["caption"].lower()
assert not integrate(caption,{"reliable":False})["changed"]
assert integrate("dark tenor 808; male baritone",profile)["status"]=="explicit_user_style_preserved"
assert integrate("ambient 808; drums",profile)["status"]=="not_applicable"
long_caption=caption.replace("cinematic development and strong musical climax","cinematic development and strong musical climax plus enormous dramatic ending")
assert len(long_caption)>512
shorten=integrate(long_caption,profile)
assert shorten["status"]=="integrated",shorten
assert "cinematic" in shorten["caption"].lower()
assert "low male baritone" in shorten["caption"].lower()
print("QA74_OK")
print("original_chars",len(caption),"result_chars",len(result["caption"]))
print("reference_median_hz",profile["median_hz"],"register_instruction_added",result["changed"])
print("long_prompt_compaction",shorten["compactions"])

"""QA124: context-aware stress post-processing. Text-only; does not edit ACE-Step."""
import json,re,sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
root=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"
src=json.loads((root/"QA123_context_results.json").read_text(encoding="utf-8"))
def contextual(raw,pred):
    changes=[]
    def sub(word,from_mark,to_mark,reason):
        nonlocal pred
        pattern=r"(?<![А-Яа-яЁё+])"+re.escape(from_mark)+r"(?![А-Яа-яЁё])"
        updated,n=re.subn(pattern,to_mark,pred,flags=re.I)
        if n:
            changes.append({"word":word,"from":from_mark,"to":to_mark,"reason":reason})
            pred=updated
    sub("окон","ок+он","+окон","Genitive plural of окно")
    if re.search(r"\b(?:вы|мы|они|мне|нам|ему|ей|тебе|вам)\b.{0,35}\bдороги\b",raw,re.I):
        sub("дороги","дор+оги","+дороги","Predicative short adjective: dear, not roads")
    return pred,changes
out=[]
for record in src["results"]:
    fixed,changes=contextual(record["raw"],record["ruaccent"])
    out.append({**record,"reviewed":fixed,"changes":changes})
    print(record["line"],fixed,changes,flush=True)
expected={3:"+дороги",6:"+окон"}
for i,needle in expected.items():
    assert needle in out[i-1]["reviewed"],(i,out[i-1])
assert "дор+оги" in out[1]["reviewed"],"Noun roads must remain stressed on second o"
p=root/"QA124_context_guard_results.json"
p.write_text(json.dumps({"type":"text-side contextual stress validation, no singing produced","cases":len(out),"passed_target_checks":3,"results":out},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA124_PASS",p,flush=True)

"""QA126: fail-closed text-side stress validation. Does not modify Music Studio."""
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
root=Path(__file__).resolve().parent
rows=json.loads((root/"QA125_stressonnx_comparison.json").read_text(encoding="utf-8"))
old=json.loads((root/"QA124_context_guard_results.json").read_text(encoding="utf-8"))["results"]
def words(s):
    return re.findall(r"[А-Яа-яЁё]+(?:\u0301|[А-Яа-яЁё])*",s)
def stress_count(w):
    return len(re.findall(r"[аеёиоуыэюя]\u0301|ё(?!\u0301)",w,re.I))
reports=[]
for new, prev in zip(rows,old):
    assert new["raw"]==prev["raw"]
    tokens=words(new["stressonnx"])
    missing=[w for w in tokens if len(re.findall("[аеёиоуыэюя]",w,re.I))>1 and stress_count(w)!=1]
    reports.append({"line":new["line"],"raw":new["raw"],"new":new["stressonnx"],
                    "previous":prev["reviewed"],"new_unstressed_polysyllables":missing,
                    "requires_review":bool(missing)})
result={"type":"text-side quality gate only; no singing generated, no studio modification",
        "policy":"Any unstressed multi-syllable word is blocked for manual/contextual verification; passing does not guarantee correct stress",
        "total_lines":len(reports),"review_lines":sum(x["requires_review"] for x in reports),"results":reports}
(root/"QA126_stress_gate_results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA126",len(reports),"LINES REVIEW",result["review_lines"])
for row in reports:
    if row["requires_review"]: print("REVIEW",row["line"],row["new_unstressed_polysyllables"])

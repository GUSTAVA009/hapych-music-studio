"""QA127 safe ACE-Step lyric boundary: metadata only; no production patch."""
import json, unicodedata, re, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/"QA126_stress_gate_results.json").read_text(encoding="utf-8"))["results"]
def strip_marks(s):
    s=unicodedata.normalize("NFD",s)
    return "".join(c for c in s if unicodedata.category(c)!="Mn")
def plain(s):
    return strip_marks(s).replace("+","").replace("Ё","Е").replace("ё","е")
def validate(raw,annotated):
    if plain(raw)!=plain(annotated): raise ValueError("Lyrics changed by annotator")
    return raw
report=[]
for row in rows:
    raw=row["raw"]; rendered=validate(raw,row["new"])
    assert rendered==raw
    report.append({"line":row["line"],"original":raw,
      "ace_lyrics":rendered,"annotation":row["new"],
      "requires_review":row["requires_review"],
      "annotations_not_injected":True})
assert len(report)==13
assert sum(x["requires_review"] for x in report)==3
assert all(x["original"]==x["ace_lyrics"] for x in report)
out={"scope":"ACE Step input boundary dry run only","production_modified":False,
 "audio_generated":False,"status":"PASS_WITH_REVIEW",
 "blocked_review_lines":[x["line"] for x in report if x["requires_review"]],
 "rule":"Original lyrics sent unchanged. Stress annotations retained as separate metadata; unreviewed stress never injected into ACE-Step.",
 "cases":report}
target=ROOT/"QA127_ace_boundary_report.json"
target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA127_PASS ORIGINAL_LYRICS_PRESERVED",len(report),"REVIEW_LINES",out["blocked_review_lines"])

"""Reuse unchanged Music Studio-generated rap cover for the voice-transferred
version of the *same* song. No new imagery generated and no old cover touched.
"""
from pathlib import Path
import sys,json,shutil,hashlib,requests
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"; D=R/"Integrations"/"RapFullTrack-QA135"
sys.path.insert(0,str(R/"app"))
from cover_art35 import cover_path
from cover_pipeline40 import generated_cover_path
o=Path(json.loads((D/"QA135_rap_source_report.json").read_text(encoding="utf8"))["file_mp3"])
n=Path(json.loads((D/"QA135_final_report.json").read_text(encoding="utf8"))["library_mp3"])
assert o.exists() and n.exists()
for fn in (cover_path,generated_cover_path):
 src=fn(o);dst=fn(n)
 if not src.exists():continue
 assert src.stat().st_size>5000 and not dst.exists()
 shutil.copy2(src,dst)
 assert hashlib.sha256(src.read_bytes()).hexdigest()==hashlib.sha256(dst.read_bytes()).hexdigest()
 print("QA135_SHARED_EXISTING_COVER",dst,flush=True)
s=requests.Session();s.trust_env=False
cover=s.get("http://127.0.0.1:7870/api/cover_status",params={"name":n.name},timeout=10)
assert cover.status_code==200
print("QA135_NEW_COVER_STATUS",cover.json(),flush=True)

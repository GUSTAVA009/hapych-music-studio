from pathlib import Path
import sys,json
R=Path.home()/"Music Studio";sys.path.insert(0,str(R/"app"))
from studio_server import prepare_request
for testcase in ["QA36","QA38"]:
 p=R/"Diagnostics"/testcase/("new_song_request.json" if testcase=="QA36" else "request.json")
 req=json.loads(p.read_text(encoding="utf-8"))
 out=prepare_request(req)
 caption=out["caption"];lyrics=out["lyrics"];omitted=out["style_plan"].get("omitted",[])
 print("TEST",testcase,"CAPTION_LEN",len(caption),"LYRICS_LEN",len(lyrics),flush=True)
 print("CAPTION",caption,flush=True)
 print("OMITTED",omitted,flush=True)
 print("LOW_BACKING_IN_LYRICS","4 low male backing harmonies" in lyrics,flush=True)
 print("LOW_BACKING_IN_CAPTION","4 low male backing harmonies" in caption,flush=True)
 print("PIANO_OUTRO_IN_CAPTION","resolved piano outro" in caption,flush=True)
 print("BARITONE_IN_CAPTION","baritone" in caption,flush=True)
 assert len(caption)<=512 and len(lyrics)<=4096
 if testcase=="QA38":
  assert "4 low male backing harmonies" in caption
  assert "resolved piano outro" in caption
  assert "baritone" in caption
  assert "4 low male backing harmonies" in lyrics
print("QA39_PROMPT_COMPILER_TEST_PASS")

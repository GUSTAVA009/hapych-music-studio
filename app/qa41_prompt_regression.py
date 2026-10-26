"""QA41 opt-in sung style regression. Rap/spoken requests should keep their delivery.
"""
import json,sys
from pathlib import Path
R=Path.home()/"Music Studio";sys.path.insert(0,str(R/"app"))
from studio_server import prepare_request
spoken=json.loads((R/"Diagnostics"/"QA38"/"request.json").read_text(encoding="utf-8"))
sung=json.loads((R/"Diagnostics"/"QA42"/"QA42_sung_request.json").read_text(encoding="utf-8"))["song"]
a,b=prepare_request(spoken),prepare_request(sung)
assert "emotive spoken male narration" in a["caption"],a["caption"]
assert "connected melodic singing" not in a["caption"],a["caption"]
assert "connected melodic singing" in b["caption"],b["caption"]
assert "spoken" not in b["caption"].lower(),b["caption"]
assert "4 low male backing harmonies" in a["caption"] and "4 low male backing harmonies" in b["caption"]
assert "resolved piano outro" in b["caption"]
assert all(x["supported"] for x in b["effects_plan"])
assert len(a["caption"])<=512 and len(b["caption"])<=512
assert "Город, город, дай мне свет." in b["lyrics"]
print("QA41_SUNG_DELIVERY_OPTIN_TEST_PASS",
      "legacy_spoken_untouched",a["caption_length"],
      "explicit_sung",b["caption_length"],flush=True)

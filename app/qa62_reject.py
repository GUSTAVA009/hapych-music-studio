"""QA62 post-listening rejection.
Never alter original QA54, user uploads, running models or studio.
"""
from pathlib import Path
import json,datetime
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA62"
p=D/"qa62_owner_rejected.json"
report={
 "recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "qa62_openvoice_t01":{"status":"rejected","reason":"Owner listened: harsh fragmented phonemes and wrong musical fit"},
 "qa62_openvoice_t03":{"status":"rejected","reason":"Owner listened: harsh fragmented phonemes and wrong musical fit"},
 "owner_comment_ru":"Обе версии ужасны, вообще не впопад и на каждой букве режет просто.",
 "decision":"Neither OpenVoiceV2 conversion may be promoted or deployed; retain QA54 baseline",
 "next_action":"Time-local F0 and voicing audit; source vs QA54 vs QA62; reject model changes until real audible improvement.",
 "working_qa54_model":"alex_clean_qa44_v2",
 "qa62_not_deployed":True,
 "more_openvoice_parameter_search":False,
 "preserve_user_recordings":True}
p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA62_REJECTED_RECORDED",str(p))

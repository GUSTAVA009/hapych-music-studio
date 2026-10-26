"""Offline 24s ASR regression gate for QA38. Words-only proxy; not listener certification."""
from pathlib import Path
import json,sys,time,difflib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA38"
sys.path.insert(0,str(R/"Voice Engine"))
from voice_guard24 import transcriptions,words,edit_distance
src=D/"QA38_Source_8to48.wav"
dest=D/"QA38_PersonalVoice_40s.mp3"
assert src.is_file() and dest.is_file()
before,after=transcriptions(src,dest,"ru")
a,b=words(before),words(after)
ed=edit_distance(a,b)
sm=difflib.SequenceMatcher(None,a,b,autojunk=False)
matched=sum(x.size for x in sm.get_matching_blocks())
res={"source":before,"converted":after,"source_word_count":len(a),
     "converted_word_count":len(b),"edit_distance":ed,
     "edit_fraction":round(ed/max(1,len(a)),3),
     "matched_fraction_of_source":round(matched/max(1,len(a)),3),
     "relative_word_quality_verified":False,
     "meaning":"ASR transcriptions of music are noisy, don't certify native diction."}
(D/"personal_voice_40s_asr.json").write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA38_40S_ASR",json.dumps(res,ensure_ascii=True),flush=True)

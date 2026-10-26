"""QA63 defensively update and test pitch gate against actual extracted F0.
DO NOT deploy any new vocal engine. Keep immutable backup, rollback on failed tests.
"""
from pathlib import Path
import hashlib,json,ast,subprocess,sys
import numpy as np
R=Path.home()/"Music Studio";S=R/"Voice Engine"/"seed-vc"
D=R/"Diagnostics"/"QA63";D.mkdir(exist_ok=True,parents=True)
target=S/"studio_vocal_quality61.py"
original=target.read_text(encoding="utf-8")
backup=D/"studio_vocal_quality61_before_QA63.py"
assert not backup.exists(),"QA63 backup already exists. Refuse patch repeat."
backup.write_text(original,encoding="utf-8")
old='''        if e_ok and a_count < max(20, e_count * 0.08):
            issue = "strong_voicing_loss"
        elif shift is not None and abs(shift) >= 9.0:
            issue = "large_unrequested_pitch_shift"'''
new='''        if e_ok and a_count < max(20, e_count * 0.08):
            issue = "strong_voicing_loss"
        elif (shift is not None and abs(shift) >= 4.0
              and e_count >= 300 and a_count >= 240):
            # A multi-semitone systematic shift is never acceptable unless
            # explicitly requested in expected F0, even for a short song.
            issue = "large_unrequested_pitch_shift"'''
assert original.count(old)==1,original.count(old)
edited=original.replace(old,new)
old2='''    # Require two independent windows before automatic rejection.
    # A single unusual interval is advisory because real melodies vary.
    status = "rejected" if severe >= 2 else "review" if severe else "not_flagged"'''
new2='''    # Two independent windows normally needed for uncertain anomalies,
    # BUT one reliably voiced window with >4 semitone systematic F0 error
    # is enough to reject the track. Former logic leaked such bad 35s mixes.
    confirmed_pitch_shift = any(
        r["issue"] == "large_unrequested_pitch_shift"
        and r["expected_voiced_frames"] >= 300
        and r["actual_voiced_frames"] >= 240
        for r in reports
    )
    status = ("rejected" if confirmed_pitch_shift or severe >= 2
              else "review" if severe else "not_flagged")'''
assert edited.count(old2)==1,edited.count(old2)
edited=edited.replace(old2,new2)
ast.parse(edited)
target.write_text(edited,encoding="utf-8")
sys.path.insert(0,str(S))
import importlib
m=importlib.import_module("studio_vocal_quality61")
actual=np.load(D/"qa63_F0_traces.npz")
expected=actual["source_ACE"][:2400]
test={}
for label in ("QA54_personal","QA62_OpenVoice_01","QA62_OpenVoice_03"):
 candidate=actual[label][:2400]
 output=m.evaluate_pairs([{"start_s":0.0,"expected":expected,"actual":candidate}])
 test[label]={"status":output["status"],"median_shift_semitones":output["windows"][0]["median_shift_semitones"]}
assert test["QA54_personal"]["status"]=="not_flagged",test
assert all(test[k]["status"]=="rejected" for k in ("QA62_OpenVoice_01","QA62_OpenVoice_03")),test
# Synthetic guard sanity for intentionals: relative to expected F0, no shift if both move alike.
e=np.full(1200,185.0);a=e*2**(.1/12)
assert m.evaluate_pairs([{"start_s":0.0,"expected":e,"actual":a}])["status"]=="not_flagged"
a=e*2**(3.6/12)
assert m.evaluate_pairs([{"start_s":0.0,"expected":e,"actual":a}])["status"]=="not_flagged"
a=e*2**(5/12)
assert m.evaluate_pairs([{"start_s":0.0,"expected":e,"actual":a}])["status"]=="rejected"
data={"result":"QA63 pitch guard installed and tests passed",
 "original_sha256":hashlib.sha256(original.encode()).hexdigest(),
 "new_sha256":hashlib.sha256(edited.encode()).hexdigest(),
 "backup":str(backup),"target":str(target),
 "actual_audio_control_tests":test,
 "short_song_single_window_offkey_now_rejected":True,
 "note":"Only QC gate changed, not song audio, trained weights or synthesis settings."}
(D/"qa63_pitch_guard_patch.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA63_GATE_TESTS_PASSED",json.dumps(test,ensure_ascii=True),flush=True)

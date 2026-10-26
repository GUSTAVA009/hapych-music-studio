"""QA58 no-F0-smoothing quality check on precisely identical QA54 dry vocal source.
"""
import json,sys
from pathlib import Path
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA58";Q=R/"Diagnostics"/"QA54"
sys.path.insert(0,str(R/"Voice Engine"))
from voice_guard42 import check
files=sorted((D/"synth").glob("vc_*.wav"))
assert len(files)==1,files
quality=json.loads((D/"synth"/"register_report.json").read_text(encoding="utf-8"))
report=check(Q/"QA54_CFG090_35s.source.wav",files[0],D/"qa58_voicecheck.json","ru")
old=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
res={"test":"raw RMVPE F0 vs stabilized original QA54",
  "old_quality":{"speaker_cosine":old["speaker_embedding_cosine"],
   "drop_events":old["voice_check"]["metrics"]["energy_dip_events"],
   "drop_fraction":old["voice_check"]["metrics"]["relative_missing_vocal_frames"],
   "max_dip":old["voice_check"]["metrics"]["longest_energy_dip_s"]},
  "new_quality":{"speaker_cosine":quality.get("speaker_embedding_cosine"),
   "drop_events":report["metrics"]["energy_dip_events"],
   "drop_fraction":report["metrics"]["relative_missing_vocal_frames"],
   "max_dip":report["metrics"]["longest_energy_dip_s"],
   "pitch_status":quality.get("pitch_consistency",{}).get("status"),
   "f0_revision":quality.get("f0_cleanup",{}).get("revision"),
   "diffusion_chunks":quality.get("stitching",{}).get("diffusion_chunks")},
  "same_source_and_reference":True,"production_unchanged":True,"phoneme_fidelity_unverified":True}
(D/"qa58_comparison.json").write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA58_MEL_SCORE",json.dumps(res,ensure_ascii=True),flush=True)

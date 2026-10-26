"""Document QA63 production integration and the user's auditory verdict.
Archive remains on local workstation; no more audio uploads.
"""
from pathlib import Path
import json,datetime,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA63"
smoke=json.loads((D/"qa63_integration_smoke_report.json").read_text(encoding="utf-8"))
guard=json.loads((D/"qa63_pitch_guard_patch.json").read_text(encoding="utf-8"))
patch=json.loads((D/"qa63_production_patch.json").read_text(encoding="utf-8"))
assert smoke["ok"] and smoke["trained"] and smoke["model"]=="alex_clean_qa44_v2"
assert "studio54" in patch["updated_pipeline"]
result={
 "time":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "user_verdict_QA62":"Both variants sound awful and severely cut phonemes, out of key",
 "qa62_status":"permanently rejected",
 "extracted_pitch_source_vs_QA62":{"tau010_median_semitones":-8.98,"tau030_median_semitones":-8.96},
 "qa63_qc_gate":{"success":True,"qa54_control":"not_flagged","qa62_both":"rejected",
   "source_code_backup":guard["backup"]},
 "production_wiring":{"old":"voice_bridge25 -> convert_track_studio25; server trained=False",
   "new":"voice_bridge25 -> convert_track_studio54_cfg090; for matched Alex KZNT recorded voice trained=True",
   "unrecognized_profile_uses_base":True,
   "rejected_QA59_or_OpenVoice_never_deployed":True,
   "backup_directory":patch["backup"]},
 "end_to_end_test":{"success":smoke["ok"],"voice_model":smoke["model"],
   "source_length_s":smoke["duration_seconds"],"mel_chunks":smoke["mel_chunks"],
   "speaker_cosine_proxy":smoke["speaker_cosine"],
   "detected_drop_events":smoke["drop_events"],
   "max_dropout_seconds":smoke["longest_dip_s"],
   "user_hearing_assessment_pending":True,
   "tested_mp3":smoke["path"]},
 "studio_healthy_after_restart":True,
 "vocal_naturalness_fixed":False,
 "remaining_faults":"Russian consonant/vowel continuity, missing word endings, singer timbre and style; requires singing-specific data/model changes; do not promise success from ASR.",
 "old_songs_user_voice_records_unchanged":True}
(D/"QA63_FINAL_INTEGRATION_REPORT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA63_REPORT_SAVED",str(D/"QA63_FINAL_INTEGRATION_REPORT.json"))

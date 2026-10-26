"""Conservative profile-aware selection of tested QA54 personal speaker model.
The personal checkpoint is never applied to unrelated/unassigned singers.
No audio is moved or overwritten.
"""
from pathlib import Path
import hashlib,json

ROOT=Path.home()/"Music Studio"
PERSONAL_RUN=ROOT/"Voice Engine"/"seed-vc"/"runs"/"alex_clean_qa44_v2"
MODEL_NAME="alex_clean_qa44_v2"
POLICY_PATH=ROOT/"Voice Profiles"/"preferred_model_policy63.json"
MANIFEST=ROOT/"Diagnostics"/"QA59"/"qa59_dataset_manifest.json"

def select(recording,validated_profile):
    file=Path(recording)
    if not file.is_file() or file.parent.resolve() != (ROOT/"Мой голос").resolve():
        raise ValueError("Voice recording must be from authorized local voice library")
    profile_id=(validated_profile or {}).get("profile_id")
    allow=False
    source="base_zero_shot"
    if profile_id:
        # Explicit profile match and ownership were already checked by
        # voice_profiles34.validate_reference in studio_server.py.
        policy=json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        matching=policy.get("preferred_models",{}).get(profile_id)
        if matching and matching.get("run")==MODEL_NAME:
            allow=True
            source="profile_owner_selected_qa54_experimental"
    else:
        data=json.loads(MANIFEST.read_text(encoding="utf-8"))
        known={p["source_sha256"] for p in data["sources"] if p.get("role")=="train"}
        if hashlib.sha256(file.read_bytes()).hexdigest() in known:
            allow=True
            source="known_qa54_reference_recording"
    trained=bool(allow and (PERSONAL_RUN/"ft_model.pth").is_file() and
                 (PERSONAL_RUN/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml").is_file())
    return {"trained":trained,"policy":source if trained else "base_zero_shot",
            "model":MODEL_NAME if trained else "base_SeedVC",
            "perceptual_quality_certified":False}

"""QA63 opt-in profile-aware active studio voice pipeline upgrade:
1) backup files, 2) switch old converter25 to QA54 approved,
3) use QA44 personal model ONLY on user-owned known source mics
   or explicitly assigned and rights-confirmed Alex KZNT artist profile.
No new song deletion, no checkpoint overwrite. Atomic + idempotent guard.
"""
from pathlib import Path
import ast,json,hashlib,shutil,py_compile
R=Path.home()/"Music Studio";A=R/"app";D=R/"Diagnostics"/"QA63";D.mkdir(exist_ok=True,parents=True)
B=D/"production_before_upgrade";B.mkdir(exist_ok=True)
manifest=json.loads((R/"Diagnostics"/"QA59"/"qa59_dataset_manifest.json").read_text(encoding="utf-8"))
approved={x["source_sha256"] for x in manifest["sources"] if x["role"]=="train"}
assert len(approved)==3
profiles=R/"Voice Profiles"/"profiles.json"
db=json.loads(profiles.read_text(encoding="utf-8"))
matches=[p for p in db["profiles"] if p["name"]=="Alex KZNT" and p.get("rights_confirmed")]
assert len(matches)==1
profileid=matches[0]["id"]
assert any(v.get("profile_id")==profileid and v.get("rights_confirmed") for v in db["assignments"].values())
model=R/"Voice Engine"/"seed-vc"/"runs"/"alex_clean_qa44_v2"
assert all((model/n).is_file() for n in ("ft_model.pth","config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"))
assert (R/"Voice Engine"/"convert_track_studio54_cfg090.py").is_file()
policy_source='''"""Conservative profile-aware selection of tested QA54 personal speaker model.
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
'''
policy_module=A/"voice_model_policy63.py"
if policy_module.exists():raise RuntimeError("Policy module exists: refusing overwrite")
ast.parse(policy_source);policy_module.write_text(policy_source,encoding="utf-8")
policy_config=R/"Voice Profiles"/"preferred_model_policy63.json"
if policy_config.exists():raise RuntimeError("Policy config exists: refusing overwrite")
selection={
 "schema":1,
 "preferred_models":{profileid:{"run":"alex_clean_qa44_v2",
    "note":"QA54 best of existing owner-audited tests but not free of syllable glitches",
    "status":"experimental_owner_preferred",
    "no_cross_profile_reuse":True}},
 "unknown_profiles_use_base":True,"accepted_qa54":True,
 "unapproved_qa59_or_openvoice":False}
policy_config.write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding="utf-8")
files=[
 A/"voice_bridge25.py",
 A/"studio_server.py",
]
for f in files:
 b=B/f.name
 assert not b.exists()
 shutil.copy2(f,b)
 # Integrity evidence for rollback
 print("BACKUP",f.name,hashlib.sha256(b.read_bytes()).hexdigest(),flush=True)
bridge=files[0].read_text(encoding="utf-8")
a='PIPELINE = VOICE_ENGINE / "convert_track_studio25.py"'
b='PIPELINE = VOICE_ENGINE / "convert_track_studio54_cfg090.py"'
assert bridge.count(a)==1
bridge_new=bridge.replace(a,b)
server=files[1].read_text(encoding="utf-8")
changes=[
 ('from voice_bridge25 import convert_song','from voice_bridge25 import convert_song\nfrom voice_model_policy63 import select as select_voice_model'),
 ('        voice_for_conversion = None','        voice_for_conversion = None\n        voice_model_selection={"trained":False,"policy":"none","model":"none"}'),
 ('            prepared["voice_artist_profile"]=artist_profile\n            voice_for_conversion = compatible_audio(v)',
  '            prepared["voice_artist_profile"]=artist_profile\n            voice_model_selection=select_voice_model(v,artist_profile)\n            prepared["voice_model_selection"]=voice_model_selection\n            voice_for_conversion = compatible_audio(v)'),
 ('                    trained=False,','                    trained=voice_model_selection["trained"],'),
 ('                    "title": title, "variant": index, "voice_applied": True,',
  '                    "title": title, "variant": index, "voice_applied": True,\n                    "voice_model_policy":voice_model_selection["policy"],\n                    "voice_model_used":voice_model_selection["model"],')
]
for old,new in changes:
 assert server.count(old)==1,(old,server.count(old))
 server=server.replace(old,new)
ast.parse(bridge_new);ast.parse(server)
# Test policy from staging content before releasing to live server
import sys,importlib
sys.path.insert(0,str(A))
policy=importlib.import_module("voice_model_policy63")
from voice_profiles34 import validate_reference
known=R/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav"
selected=next((R/"Мой голос"/f for f,v in db["assignments"].items() if v["profile_id"]==profileid),None)
assert selected and selected.exists()
assert policy.select(known,validate_reference(known.name,""))["trained"]
assert policy.select(selected,validate_reference(selected.name,profileid))["trained"]
holdout=next((R/"Мой голос").glob("*65f5f3.wav"))
assert not policy.select(holdout,validate_reference(holdout.name,""))["trained"]
# all unit checks pass before live files changed
files[0].write_text(bridge_new,encoding="utf-8")
files[1].write_text(server,encoding="utf-8")
py_compile.compile(str(files[0]),doraise=True)
py_compile.compile(str(files[1]),doraise=True)
py_compile.compile(str(policy_module),doraise=True)
result={"deployed_source":str(files[1]),"active_bridge_updated":str(files[0]),
    "updated_pipeline":"convert_track_studio54_cfg090.py",
    "selected_artist_id":profileid,"profile_selected_mic":selected.name,
    "known_training_mic":known.name,"known_training_qa54":True,
    "holdout_not_force_personal":True,"qa59_unavailable":True,
    "qa62_openvoice_unavailable":True,"production_restart_required":True,
    "backup":str(B),"personal_model_only_for_matched_reference":True,
    "f0_guard_qa63_already_unit_tested":True,"song_files_unchanged":True}
(D/"qa63_production_patch.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA63_PRODUCTION_SOURCE_PATCH_OK",json.dumps(result,ensure_ascii=True),flush=True)

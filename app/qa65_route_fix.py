from pathlib import Path
import json,py_compile,shutil,datetime,hashlib
root=Path.home()/"Music Studio";app=root/"app";src=app/"studio_server.py"
original=src.read_text(encoding="utf-8")
backup=app/("studio_server.py.pre-qa65-route-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")+".bak")
shutil.copy2(src,backup)
old='''        request_file.write_text(json.dumps({"preparation": prepared,
            "settings": {key: value for key, value in settings.items() if key not in refs}},
            ensure_ascii=False, indent=2), encoding="utf-8")'''
new='''        request_file.write_text(json.dumps({"preparation": prepared,
            "voice_routing": {
                "voice_requested":bool(data.get("use_voice") and data.get("voice")),
                "apply_voice":bool(data.get("apply_voice",True)),
                "selected_recording":str(data.get("voice") or ""),
                "validated_profile_id":(prepared.get("voice_artist_profile") or {}).get("profile_id"),
                "trained":bool(voice_model_selection["trained"]),
                "model":voice_model_selection["model"],
                "policy":voice_model_selection["policy"],
                "pipeline":"convert_track_studio54_cfg090.py"},
            "settings": {key: value for key, value in settings.items() if key not in refs}},
            ensure_ascii=False, indent=2), encoding="utf-8")'''
assert original.count(old)==1
modified=original.replace(old,new)
old2='''                    "voice_model_used":voice_model_selection["model"],
                })'''
new2='''                    "voice_model_used":voice_model_selection["model"],
                    "voice_pipeline":"convert_track_studio54_cfg090.py",
                    "voice_model_trained":bool(voice_model_selection["trained"]),
                })'''
assert modified.count(old2)==1
modified=modified.replace(old2,new2)
old3='''                    "voice_check_note":"Перенос тембра не применён: "+str(voice_exc),
                })'''
new3='''                    "voice_check_note":"Перенос тембра не применён: "+str(voice_exc),
                    "voice_model_policy":voice_model_selection["policy"],
                    "voice_model_used":voice_model_selection["model"],
                    "voice_model_trained":bool(voice_model_selection["trained"]),
                    "voice_pipeline":"convert_track_studio54_cfg090.py",
                })'''
assert modified.count(old3)==1
modified=modified.replace(old3,new3)
temp=app/"studio_server.qa65.tmp.py";temp.write_text(modified,encoding="utf-8")
py_compile.compile(str(temp),doraise=True)
# verification of route guarantees, no unrelated files modified
assert "from voice_bridge25 import convert_song" in modified
assert "trained=voice_model_selection[\"trained\"]" in modified
assert "PIPELINE = VOICE_ENGINE / \"convert_track_studio54_cfg090.py\"" in (app/"voice_bridge25.py").read_text(encoding="utf-8")
assert src.read_text(encoding="utf-8")==original
temp.replace(src)
result={"status":"patch_written","backup":str(backup),
 "old_sha256":hashlib.sha256(original.encode()).hexdigest(),
 "new_sha256":hashlib.sha256(modified.encode()).hexdigest(),
 "voice_selection_logged_per_request":True,"actual_voice_model_stored_in_track_metadata":True,
 "default_voice_policy_unchanged":True,"all_voice_samples_untouched":True,
 "qa54_pipeline_selected":True}
(root/"Diagnostics"/"QA65").mkdir(parents=True,exist_ok=True)
(root/"Diagnostics"/"QA65"/"qa65_route_fix.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=True))

"""QA100 read-only local A/B access, surgical preview integration.
No voice algorithm, jobs, models, originals, or existing tracks modified.
"""
from pathlib import Path
import ast,json,datetime,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA100-LowRegister"
app=R/"app";server=app/"studio_server.py";ui=app/"ui"/"index.html"
preview=app/"ui"/"qa100_compare.html"
base=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.mp3"
test=D/"QA100_LowBaritone_MyVoice_35s.mp3"
assert preview.is_file() and base.is_file() and test.is_file()
assert base.stat().st_size>200000 and test.stat().st_size>200000
old=server.read_text(encoding="utf-8")
old_html=ui.read_text(encoding="utf-8")
backup_server=D/"studio_server_before_QA100.py.bak"
backup_ui=D/"index_before_QA100.html.bak"
assert not backup_server.exists() and not backup_ui.exists(),"QA100 already staged: refuse double-patching"
anchor='        if path == "/qa90-style-compare":'
insert='''        if path == "/qa100-compare":
            # QA100: read-only fixed A/B comparison, no generation or model change.
            return self.send_file(UI / "qa100_compare.html")
        if path == "/api/qa100-audio/qa54":
            return self.send_file(ROOT / "Diagnostics" / "QA54" / "QA54_CFG090_35s.mp3")
        if path == "/api/qa100-audio/qa100":
            return self.send_file(ROOT / "Diagnostics" / "QA100-LowRegister" / "QA100_LowBaritone_MyVoice_35s.mp3")
'''
assert old.count(anchor)==1
new=old.replace(anchor,insert+anchor)
assert new.count('"/qa100-compare"')==1 and new.count('"/api/qa100-audio/qa100"')==1
new=new.replace('qa90-native-style-default+voice-profile-alerts+ru-vocal51-guard',
                'qa90-native-style-default+voice-profile-alerts+ru-vocal51-guard+qa100-readonly-preview')
assert new!=old
ast.parse(new)
marker='<button type="button" class="outline-btn" id="checkHealth"><svg class="ico"><use href="#i-refresh"/></svg> Проверить соединение</button>'
replacement=marker+'<p class="muted small"><a href="/qa100-compare" target="_blank" rel="noopener noreferrer">Сравнить QA54 и QA100 — тест непрерывности голоса</a></p>'
assert old_html.count(marker)==1
new_html=old_html.replace(marker,replacement)
backup_server.write_text(old,encoding="utf-8")
backup_ui.write_text(old_html,encoding="utf-8")
server.write_text(new,encoding="utf-8")
ui.write_text(new_html,encoding="utf-8")
record={"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "preview_only":True,"live_voice_code_not_changed":True,"qa54_model_not_changed":True,
 "audio_paths_fixed":True,"audio_source_qa54":str(base),
 "audio_source_qa100":str(test),
 "server_backup":str(backup_server),"ui_backup":str(backup_ui),
 "route":"/qa100-compare","html_link_settings":True,
 "source_sha256":hashlib.sha256(old.encode()).hexdigest(),
 "installed_sha256":hashlib.sha256(new.encode()).hexdigest()}
(D/"qa100_preview_patch.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA100_PREVIEW_PATCH_COMPILED",json.dumps(record,ensure_ascii=True),flush=True)

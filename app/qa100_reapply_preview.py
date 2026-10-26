"""Idempotent QA100 read-only preview re-apply after verified rollback.
Use immutable backups; only server route and Settings link, no model logic.
"""
from pathlib import Path
import ast,hashlib,json
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA100-LowRegister"
server=R/"app"/"studio_server.py";ui=R/"app"/"ui"/"index.html"
source=(D/"studio_server_before_QA100.py.bak").read_text(encoding="utf-8")
html=(D/"index_before_QA100.html.bak").read_text(encoding="utf-8")
assert 'qa100-readonly-preview' not in source
assert 'href="/qa100-compare"' not in html
anchor='        if path == "/qa90-style-compare":'
addition='''        if path == "/qa100-compare":
            return self.send_file(UI / "qa100_compare.html")
        if path == "/api/qa100-audio/qa54":
            return self.send_file(ROOT / "Diagnostics" / "QA54" / "QA54_CFG090_35s.mp3")
        if path == "/api/qa100-audio/qa100":
            return self.send_file(ROOT / "Diagnostics" / "QA100-LowRegister" / "QA100_LowBaritone_MyVoice_35s.mp3")
'''
assert source.count(anchor)==1
modified=source.replace(anchor,addition+anchor).replace("qa90-native-style-default+voice-profile-alerts+ru-vocal51-guard","qa90-native-style-default+voice-profile-alerts+ru-vocal51-guard+qa100-readonly-preview")
ast.parse(modified)
marker='<button type="button" class="outline-btn" id="checkHealth"><svg class="ico"><use href="#i-refresh"/></svg> Проверить соединение</button>'
assert html.count(marker)==1
ui_new=html.replace(marker,marker+'<p class="muted small"><a href="/qa100-compare" target="_blank" rel="noopener noreferrer">Сравнить QA54 и QA100 — тест непрерывности голоса</a></p>')
server.write_text(modified,encoding="utf-8")
ui.write_text(ui_new,encoding="utf-8")
assert (R/"app"/"ui"/"qa100_compare.html").is_file()
print("QA100_PREVIEW_REAPPLIED_CHECKED",len(modified),len(ui_new),flush=True)

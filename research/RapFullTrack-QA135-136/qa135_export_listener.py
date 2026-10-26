"""Local listen page and source/final exports. Open by double-clicking
the HTML on the Music Studio PC; audio is fetched from the verified
localhost Music Studio audio API, so no extra server routes are required.
"""
from pathlib import Path
import requests,shutil,sys,json,hashlib,re
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
v=json.loads((D/"QA135_final_report.json").read_text(encoding="utf8"))
o=json.loads((D/"QA135_rap_source_report.json").read_text(encoding="utf8"))
name=R/"app"/"ui"/"qa135_rap_compare.html"
assert name.exists()
html=name.read_text(encoding="utf8")
base="http://127.0.0.1:7870"
for section in ('api/audio','api/cover'):
 html=html.replace(f'"/{section}/',f'"{base}/{section}/')
html=html.replace('href="/"',f'href="{base}/"')
folder=R/"Exports"/"QA135_Gromche_Rap_MyVoice"
folder.mkdir(parents=True,exist_ok=True)
dst=folder/"QA135_Listen.html"
dst.write_text(html,encoding="utf8")
assert html.count("<audio controls")==2
assert 'Сохранить MP3' in html
assert "http://127.0.0.1:7870/api/audio/" in html
expected={
 "Громче_чем_вчера_РЭП_МОЙ_ГОЛОС.mp3":Path(v["library_mp3"]),
 "Громче_чем_вчера_РЭП_МОЙ_ГОЛОС_МАСТЕР.wav":Path(v["library_master_wav"]),
 "Громче_чем_вчера_РЭП_ОРИГИНАЛ.mp3":Path(o["file_mp3"])
}
for name,src in expected.items():
 assert src.is_file()
 output=folder/name
 if not output.exists():shutil.copy2(src,output)
 assert hashlib.sha256(src.read_bytes()).hexdigest()==hashlib.sha256(output.read_bytes()).hexdigest()
 print("QA135_EXPORT",name,round(output.stat().st_size/1048576,2),"MB",flush=True)
readme=f"""ГРОМЧЕ, ЧЕМ ВЧЕРА — РЭП
Длительность: 2:30.65. 100 BPM. Мужской русский вокал, 808-бас.
Новая генерация Music Studio, 27 октября 2026.

1. Громче_чем_вчера_РЭП_МОЙ_ГОЛОС.mp3
   Главный результат: перенос тембра ApexSVC, пресет QA133 «Защита согласных».
2. Громче_чем_вчера_РЭП_МОЙ_ГОЛОС_МАСТЕР.wav
   Несжатый мастер WAV (24-bit).
3. Громче_чем_вчера_РЭП_ОРИГИНАЛ.mp3
   Исходный вокал ACE-Step без переноса тембра.
4. QA135_Listen.html
   Страница A/B; открой двойным щелчком на компьютере, где запущена Music Studio.

Файлы также доступны в Music Studio > «Мои треки» и «Мастер WAV».
Пресет сохранён: Voice Profiles\\presets\\QA133_ConsonantProtection_ApexSVC.json
Предупреждение: хотя длительность и ноты сохранились, Whisper
показывает изменение части слов после конвертации; проверка на слух нужна.
Настройка сохранена в отдельный пресет, не заменяет стандартный Seed-VC
в интерфейсе при последующих генерациях.
"""
(folder/"README.txt").write_text(readme,encoding="utf8")
s=requests.Session();s.trust_env=False
links=re.findall(r'https?://127\.0\.0\.1:7870/api/(?:audio|cover)/[^"]+',html)
assert len(links)>=5,len(links)
for url in set(links):
 resp=s.get(url,stream=True,timeout=12)
 assert resp.status_code==200,(url,resp.status_code)
 resp.close()
print("QA135_LISTEN_PAGE_EXPORTED",dst,flush=True)

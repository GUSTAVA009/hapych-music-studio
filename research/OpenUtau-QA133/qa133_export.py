"""Package QA133 deliverables for listening in Music Studio/Exports.
Copies only generated song WAV/MP3 and QA metadata; leaves runtime and the
owner microphone recordings unmodified. No public hosting/upload.
"""
from pathlib import Path
import json,hashlib,shutil,zipfile,sys
import soundfile as sf
sys.stdout.reconfigure(encoding="utf8")
ROOT=Path.home()/"Music Studio"
R=ROOT/"Integrations"/"OpenUtau-QA129"/"QA132-KogdaPronunciation"/"QA133-FinalDiction"
O=R/"QA133-OwnerVoice"
EXPORT=ROOT/"Exports"/"QA133_RussianVocal_20261026"
EXPORT.mkdir(parents=True,exist_ok=True)
transfer=json.loads((O/"QA133_owner_transfer.json").read_text(encoding="utf8"))
render=json.loads((R/"QA133_render_report.json").read_text(encoding="utf8"))
asr_source=json.loads((R/"QA133_asr_comparison.json").read_text(encoding="utf8"))
asr_owner=json.loads((O/"QA133_owner_asr_report.json").read_text(encoding="utf8"))
acoustics=json.loads((O/"QA133_objective_metrics.json").read_text(encoding="utf8"))
speaker=json.loads((O/"QA133_speaker_proxy.json").read_text(encoding="utf8"))
assert transfer["status"]=="rendered_pending_QA"
assert render["status"]=="two_acoustic_candidates_assembled"
assert all(item["wer"]==0 for item in asr_source["cases"]["A_native_dosht"]["lines"])
assert [item["WER"] for item in asr_owner["cases"]["main_identity"]["lines"]]==[.2,0,0,0]
assert speaker["cases"]["main_identity"]>speaker["cases"]["consonants"]
items=[
 ("01_MyVoice_Main.wav",Path(transfer["candidates"]["main_identity"]["wav"])),
 ("01_MyVoice_Main.mp3",Path(transfer["candidates"]["main_identity"]["mp3"])),
 ("02_MyVoice_Consonants.wav",Path(transfer["candidates"]["consonants"]["wav"])),
 ("02_MyVoice_Consonants.mp3",Path(transfer["candidates"]["consonants"]["mp3"])),
 ("03_DiffSinger_Diction_Passed.wav",Path(render["cases"]["A_native_dosht"]["wav"])),
 ("03_DiffSinger_Diction_Passed.mp3",Path(render["cases"]["A_native_dosht"]["mp3"])),
 ("04_DiffSinger_SoftDozhd.mp3",Path(render["cases"]["B_soft_doshch"]["mp3"])),
]
manifest=[]
for name,orig in items:
 assert orig.is_file()
 dst=EXPORT/name
 shutil.copy2(orig,dst)
 if dst.suffix==".wav":
  assert abs(sf.info(dst).duration-20.88)<.06
 manifest.append({"file":name,"size_bytes":dst.stat().st_size,
                  "sha256":hashlib.sha256(dst.read_bytes()).hexdigest()})
html=r'''<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QA133 — HAPYCH Music Studio | Прослушивание</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}
body{font:16px/1.5 "Segoe UI",Arial,sans-serif;color:#eff4ff;background:#0d1119;margin:0;padding:28px 16px}
main{max-width:940px;margin:0 auto}
.top{font-size:12px;letter-spacing:.17em;color:#8bace1;font-weight:750;margin-bottom:12px}
h1{font-size:clamp(26px,4.5vw,39px);line-height:1.17;margin:0 0 14px}
h2{font-size:20px;margin:0 0 9px}
p{color:#b6c1d4;margin:9px 0 15px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:15px}
.card{background:#192131;border:1px solid #35435b;border-radius:18px;padding:22px;margin:12px 0}
.card.primary{border-color:#7d8eef;background:#1b2440}
.meta{color:#aec6e8;font-size:13px;font-weight:650}
audio{display:block;width:100%;margin:17px 0 9px}
.links{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
a{color:#dce8ff;background:#2a3a58;border:1px solid #425578;border-radius:9px;text-decoration:none;padding:8px 12px;font-size:14px}
a:hover{background:#38527b}
.notice{background:#212838;border:1px solid #404e65;border-radius:14px;padding:17px 21px;margin:16px 0}
.notice strong{color:#fff}ol{color:#dce6f5;padding-left:23px}
small{color:#9caec4}.lyric{white-space:pre-line;line-height:1.7;border-left:3px solid #657da5;padding-left:15px;color:#e0eaff}
</style></head><body><main>
<div class="top">HAPYCH · MUSIC STUDIO · QA133</div>
<h1>Новый русский вокал — готовые аудиопробы</h1>
<p>Все треки имеют продолжительность <strong>20,88 секунды</strong>. Слова «когда», «дождь» и «мою» исправлены на уровне фонемного синтеза. Это реальные готовые WAV и MP3, а не превью проекта.</p>
<div class="grid">
<section class="card primary"><div class="meta">01 · ОСНОВНОЙ РЕЗУЛЬТАТ</div><h2>Твой тембр — приоритет сходства</h2>
<p>Перенос на основе двух твоих микрофонных записей. Тональность сохранена, автотюн выключен, склеек с чужим певцом нет.</p>
<audio controls preload="metadata" src="01_MyVoice_Main.mp3"></audio>
<div class="links"><a href="01_MyVoice_Main.mp3" download>Сохранить MP3</a><a href="01_MyVoice_Main.wav" download>Сохранить WAV</a></div></section>
<section class="card"><div class="meta">02 · АЛЬТЕРНАТИВНЫЙ ПЕРЕНОС</div><h2>Твой тембр — защита согласных</h2>
<p>Вариант с более высоким приоритетом согласных и чуть иной силой переноса тембра. Для сравнения артикуляции и плавности.</p>
<audio controls preload="metadata" src="02_MyVoice_Consonants.mp3"></audio>
<div class="links"><a href="02_MyVoice_Consonants.mp3" download>Сохранить MP3</a><a href="02_MyVoice_Consonants.wav" download>Сохранить WAV</a></div></section>
<section class="card"><div class="meta">03 · КОНТРОЛЬНЫЙ ВОКАЛ</div><h2>DiffSinger — дикция без переноса</h2>
<p>Все четыре строки распознаны автоматически без ошибок. Это не твой тембр — контроль, чтобы отделить дефекты дикции от конвертера.</p>
<audio controls preload="metadata" src="03_DiffSinger_Diction_Passed.mp3"></audio>
<div class="links"><a href="03_DiffSinger_Diction_Passed.mp3" download>Сохранить MP3</a><a href="03_DiffSinger_Diction_Passed.wav" download>Сохранить WAV</a></div></section>
<section class="card"><div class="meta">04 · ВАРИАНТ ФОНЕМЫ</div><h2>DiffSinger — мягкий «дождь»</h2>
<p>Альтернативная русская реализация окончания «дождь». Только для сравнения — основной вариант использует привычное «доштʲ».</p>
<audio controls preload="metadata" src="04_DiffSinger_SoftDozhd.mp3"></audio>
<div class="links"><a href="04_DiffSinger_SoftDozhd.mp3" download>Сохранить MP3</a></div></section>
</div>
<div class="notice"><strong>Результаты проверки.</strong><p>У контрольного вокала — 4 строки из 4 без лексических ошибок распознавания. В версиях с твоим тембром — 3 строки из 4; в первой строке Whisper слышит «двоих» вместо «твоих». Проверка не обнаружила клиппинга или длительных выпадений звука. Совпадение тембра один в один и качество каждого согласного требуют оценки на слух.</p></div>
<div class="card"><h2>Текст аудиопробы</h2><p class="lyric">Мне нужен свет твоих окон
Меня услышишь и поймёшь
Когда за окном идёт дождь
Сохрани мою любовь</p>
<p><small>Модель DiffSinger Keiro Revenant (LUNAI Project) используется только для некоммерческого тестирования. Твои оригинальные аудиозаписи сохранены, исходные проекты и работающая Music Studio не изменены. Обучение на чужих записях не выполнялось.</small></p></div></main>
<script>for(const a of document.querySelectorAll('audio'))a.addEventListener('play',()=>{for(const b of document.querySelectorAll('audio'))if(a!==b)b.pause()});</script>
</body></html>'''
(EXPORT/"QA133_Compare.html").write_text(html,encoding="utf8")
readme="""HAPYCH MUSIC STUDIO — QA133, 26 октября 2026

ОСНОВНОЙ РЕЗУЛЬТАТ:
01_MyVoice_Main.mp3 / .wav — перенос на твой голос (ApexSVC, два микрофонных образца).
02_MyVoice_Consonants.mp3 / .wav — альтернативные настройки защиты согласных.
03_DiffSinger_Diction_Passed.mp3 / .wav — контрольный певец с исправленным произношением.
04_DiffSinger_SoftDozhd.mp3 — альтернативное произношение «дождь».
QA133_Compare.html — открой, чтобы послушать все 4 варианта.

Автоматическое качество: у DiffSinger 4/4 строк распознаны полностью.
В твоих двух версиях 3/4 строк. Ошибка первой строки: «двоих» вместо «твоих».
Это не скрыто и ещё требует коррекции, если на слух ошибка подтверждается.
Ни один тест не внедрён в рабочую Music Studio.
Оригиналы микрофона не перезаписаны; модели не обучались.

Источники: Keiro Revenant (LUNAI Project), только для некоммерческого тестирования.
"""
(EXPORT/"README_QA133.txt").write_text(readme,encoding="utf8")
quality={
 "status":"ready_for_user_listening_not_production_approved",
 "source_asr_line_WER":[q["wer"] for q in asr_source["cases"]["A_native_dosht"]["lines"]],
 "main_voice_asr_line_WER":[x["WER"] for x in asr_owner["cases"]["main_identity"]["lines"]],
 "alternate_voice_asr_line_WER":[x["WER"] for x in asr_owner["cases"]["consonants"]["lines"]],
 "main_voice_full_ASR_WER":asr_owner["cases"]["main_identity"]["full_WER"],
 "main_voice_speaker_similarity_relative_proxy":speaker["cases"]["main_identity"],
 "control_voice_speaker_similarity_relative_proxy":speaker["cases"]["Keiro_source"],
 "main_voice_audio_objective_metrics":acoustics["cases"]["main_identity"],
 "human_speaker_match_confirmed":False,
 "human_russian_diction_confirmed":False,
 "audio_generated_on":"2026-10-26",
 "model_training_performed":False,
 "production_music_studio_modified":False,
 "source_license":"Keiro Revenant / LUNAI Project, noncommercial audition only",
 "files":manifest}
(EXPORT/"QA133_Quality_Report.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding="utf8")
zipout=ROOT/"Exports"/"QA133_RussianVocal_Ready.zip"
with zipfile.ZipFile(zipout,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(EXPORT.iterdir()):
  if f.is_file(): z.write(f,arcname=f.name)
with zipfile.ZipFile(zipout) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(list(EXPORT.glob("*")))
print("QA133_READY_DIR",EXPORT,flush=True)
print("QA133_ZIP",zipout,round(zipout.stat().st_size/1024/1024,2),"MiB",flush=True)
print("QA133_FILES",len(manifest),"AUDIO"+" "+str((EXPORT/"01_MyVoice_Main.mp3").stat().st_size),flush=True)

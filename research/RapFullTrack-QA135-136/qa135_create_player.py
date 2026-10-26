from pathlib import Path
import html,json,urllib.parse,hashlib,sys,requests
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"; D=R/"Integrations"/"RapFullTrack-QA135"
r=json.loads((D/"QA135_final_report.json").read_text(encoding="utf8"))
source=json.loads((D/"QA135_rap_source_report.json").read_text(encoding="utf8"))
req=json.loads((D/"QA135_rap_request.json").read_text(encoding="utf8"))
full=Path(r["library_mp3"]);orig=Path(source["file_mp3"])
assert full.exists() and orig.exists()
voice="/api/audio/"+urllib.parse.quote(full.name,safe="")
raw="/api/audio/"+urllib.parse.quote(orig.name,safe="")
cover="/api/cover/"+urllib.parse.quote(full.name,safe="")
plain="\n".join(x.strip() for x in req["lyrics"].splitlines() if x.strip() and not x.strip().startswith("["))
assert "Громче, чем вчера!" in plain
esc=html.escape(plain)
page=R/"app"/"ui"/"qa135_rap_compare.html"
body=f'''<!doctype html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Громче, чем вчера — рэп · Music Studio</title>
<style>:root{{color-scheme:dark}}*{{box-sizing:border-box}}
body{{font:16px/1.55 "Segoe UI",system-ui,sans-serif;color:#eef4ff;background:radial-gradient(circle at 20% 0%,#1e3553,#10131c 64%);min-height:100vh;margin:0;padding:32px 16px}}
main{{max-width:920px;margin:0 auto}}
.kicker{{font-size:12px;letter-spacing:.16em;font-weight:700;color:#a0baff;text-transform:uppercase}}
h1{{font-size:clamp(28px,4vw,41px);line-height:1.14;margin:7px 0 12px}}
h2{{font-size:19px;margin:0 0 8px}}
p{{color:#bcc6dc;margin:8px 0 14px}}
.cover{{height:165px;width:165px;object-fit:cover;border-radius:19px;box-shadow:0 16px 50px #0007}}
.hero{{display:flex;gap:24px;align-items:center;margin:26px 0;flex-wrap:wrap}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px}}
.card{{border:1px solid #364762;background:#1d2739d9;border-radius:18px;padding:22px;margin:12px 0}}
.card.featured{{border-color:#7894f7;background:#243457}}
audio{{display:block;width:100%;margin:18px 0}}
a{{color:#e0ebff;text-decoration:none;border:1px solid #4d6186;background:#304465;border-radius:10px;padding:9px 14px;display:inline-block;font-size:14px}}
a:hover{{background:#455f88}}
.note{{font-size:13px;background:#262c37;border:1px solid #4a5667;border-radius:12px;padding:13px 16px;margin:14px 0}}
.lyrics{{white-space:pre-wrap;font:15px/1.7 "Segoe UI",system-ui,sans-serif;color:#dce7fc;max-height:350px;overflow:auto;padding:10px 15px;border-left:3px solid #7896c6}}
.label{{font-size:12px;color:#acc5ed;letter-spacing:.12em;font-weight:750}}
</style></head><body><main><div class="kicker">Music Studio · готовый трек QA135</div>
<section class="hero"><img class="cover" src="{cover}" alt="Обложка трека">
<div><h1>Громче, чем вчера — рэп</h1><p>Мелодичный русский хип-хоп / trap · 100 BPM · 2:30 · 808-бас · мужской вокал</p>
<a href="/">Открыть библиотеку Music Studio</a></div></section>
<section class="cards">
<div class="card featured"><div class="label">01 · МОЙ ГОЛОС</div><h2>Защита согласных</h2><p>Перенос твоего тембра через ApexSVC, выбранная настройка QA133. Отдельная вокальная дорожка + неизменённый инструментальный фон.</p>
<audio controls preload="metadata" src="{voice}"></audio><a href="{voice}" download>Сохранить MP3 · 320 кбит/с</a></div>
<div class="card"><div class="label">02 · ОРИГИНАЛ</div><h2>Исходный рэп без переноса</h2><p>Оригинальная генерация ACE-Step, чтобы сравнить произношение и музыкальное исполнение. Та же аранжировка и текст.</p>
<audio controls preload="metadata" src="{raw}"></audio><a href="{raw}" download>Сохранить исходный MP3</a></div></section>
<div class="note"><strong>Контроль качества:</strong> длительность 150,65 с, потерянных фрагментов вокала больше 140 мс не обнаружено, медианное отклонение F0 — 4,2 цента. Однако автоматическое распознавание выявило изменение некоторых слов после переноса голоса. Естественность русского произношения и точное совпадение тембра требуется проверить на слух.</div>
<section class="card"><h2>Текст песни</h2><div class="lyrics">{esc}</div></section>
<p style="font-size:12px">Оригинальные файлы, записанный голос и настройки модели не перезаписаны. Выбранный пресет сохранён отдельно в Voice Profiles/presets. Новая песня находится в библиотеке «Мои треки».</p>
</main><script>document.querySelectorAll('audio').forEach(x=>x.addEventListener('play',()=>document.querySelectorAll('audio').forEach(y=>{{if(y!==x)y.pause()}})))</script></body></html>'''
page.write_text(body,encoding="utf8")
s=requests.Session();s.trust_env=False
response=s.get("http://127.0.0.1:7870/qa135_rap_compare.html",timeout=12)
assert response.status_code==200 and "Защита согласных" in response.text
assert 'text/html' in response.headers.get('Content-Type','text/html')
print("QA135_PLAYER_READY",page,flush=True)
print("QA135_PLAYER_URL http://127.0.0.1:7870/qa135_rap_compare.html",flush=True)

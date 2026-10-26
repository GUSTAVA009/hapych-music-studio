"""QA38: a new, controlled, original Russian baritone music production.
Generate two independent variants; preserve existing user library and voices.
"""
import requests,sys,json
from pathlib import Path
ROOT=Path.home()/"Music Studio"
s=requests.Session();s.trust_env=False
URL="http://127.0.0.1:7870"
song={
"title":"QA38 - Тихий свет",
"style":"88 BPM, D minor. Original urban cinematic Russian noir rap ballad. Native Russian male low baritone, intimate expressive spoken rap, clean realistic consonants, natural breath, never falsetto or synthetic high voice. Opening: warm felt piano, gentle cello, distant city rain. Gradual orchestral rise, punchy warm boom bap drums, deep controlled 808 bass. Epic emotional middle with electric guitar and low strings. Powerful chorus, four LOW male background harmonies only. Wide analog stereo, soft sax fills. Musical piano resolved ending.",
"lyrics":"""[Intro - Felt Piano, Quiet Cello, Rain Bed, Slow Musical Build]
[SFX: Heavy rain on asphalt]
[Instrumental]

[Verse 1 - Natural Russian Male Baritone, Clear Spoken Rap, Unhurried]
Снова вечер, тихий двор.
Свет в окне и разговор.
Пусто там, где был наш дом.
Я иду знакомым сном.
Мы взрослеем, жизнь идёт.
За рекой туман встаёт.
Я несу с собой мечту.
И дорогу в темноту.

[Pre-Chorus - Rising Cello, Warm Harmony, Real Breath]
Слышишь, город не молчит.
Сердце верит и стучит.
За холодной полосой
Будет свет, и мы с тобой.

[Chorus - Deep Baritone, Four LOW Male Backing Voices, Wide Warm Harmonies]
Город, город, дай мне свет.
Сколько зим и сколько лет.
Я найду дорогу к дому.
К берегу давно знакомому.
[Low Male Backing Voices - Subtle Group]
(Дай мне свет.)
(Мы с тобой.)

[Instrumental Break - Epic Emotional Strings, Guitar, Saxophone, Organic Percussion, Expansive Midpoint]
[SFX: Distant car passing]

[Verse 2 - Intimate Russian Male Rap, Half-Time Piano]
Шум проспекта, свет витрин.
Я сегодня не один.
На часах уже рассвет.
На душе тяжёлых нет.
Всё плохое отпущу.
И обиды я прощу.
Пусть за окнами дожди.
Только ты меня дождись.

[Final Chorus - Confident Deep Male Baritone, Four Low Male Harmony Voices, Big Drums]
Город, город, дай мне свет.
Сколько зим и сколько лет.
Я найду дорогу к дому.
К берегу давно знакомому.
(Дай мне свет.)
(Мы с тобой.)

[Outro - Soft Felt Piano, Cello Resolution, Warm Natural Hall Tail]
Новый день нас позовёт.
Тихий свет в окно войдёт.""",
"duration":119,
"bpm":88,
"two_versions":True,
"use_voice":False,
"instrumental":False,
"mode":"new",
"vocal_language":"ru"
}
h=s.get(URL+"/api/health",timeout=8).json()
if h["job"]["status"] in ("preparing","generating","converting") or any(h.get(k,{}).get("active") for k in ("training32","training41","training23")):
 print("BLOCKED_BUSY",h["job"]);sys.exit(2)
p=s.post(URL+"/api/prepare",json=song,timeout=30)
print("PREPARE",p.status_code,flush=True)
if p.status_code!=200:print(p.text[:1000]);sys.exit(1)
r=p.json()
print("CAPTION_CHARS",r["caption_length"],"LYRIC_CHARS",len(r["lyrics"]),"SFX",[(e["effect"],e["supported"]) for e in r["effects_plan"]],"NOTES",r["structure_plan"],flush=True)
assert r["caption_length"]<=512 and len(r["lyrics"])<=4096
assert all(e["supported"] for e in r["effects_plan"])
q=ROOT/"Diagnostics"/"QA38"
q.mkdir(exist_ok=True,parents=True)
(q/"request.json").write_text(json.dumps(song,ensure_ascii=False,indent=2),encoding="utf-8")
(q/"prepared.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
gen=s.post(URL+"/api/generate",json=song,timeout=40)
print("GENERATION",gen.status_code,gen.text[:500],flush=True)
if gen.status_code!=202:sys.exit(3)

"""QA36: two-variant original urban-noir composition with musical arc and SFX.
Short, human-paced lyrics; independent male chorus, no personal voice in base test.
No extra training, no payments and no user files overwritten.
"""
import requests,sys,json,datetime
from pathlib import Path
S=requests.Session();S.trust_env=False;URL="http://127.0.0.1:7870"
song={
 "title":"QA36 - Горизонт за дождём",
 "style":"Russian cinematic noir hip hop, 90 BPM, D minor. Native Russian deep warm male baritone rap, natural pronunciation, no falsetto. Slow solo piano rain intro, cello and strings build, tight boom-bap drums and restrained 808. Epic orchestral strings, electric guitar, brass and low choir in middle. Wide chorus with four LOWER MALE backing harmonies, call response, subtle sax. Clear lead, clean space, organic dynamics, resolved piano ending.",
 "lyrics":"""[Intro - Solo Dark Piano, Quiet Strings, Gradual Build]
[SFX: Heavy rain on asphalt]
[Instrumental]

[Verse 1 - Deep Natural Russian Male Rap, Intimate]
Ночной проспект отражает огни,
Мы столько лет искали свои пути.
Под шум дождя я оставлю вчера,
За поворотом ждёт новая игра.

[Pre-Chorus - Rising Cello, Warm Bass]
И даже если станет трудно дышать,
Я знаю, что нельзя назад бежать.
Там за мостом поднимается свет,
У нашей ночи однажды будет рассвет.

[Chorus - Low Male Baritone, Four LOW Male Backing Harmonies]
Пока горят огни — мы не одни,
Навстречу утру нас ведут они.
Сквозь этот дождь, сквозь холод и туман,
Найдём свой берег, выйдем к берегам.
[Male Backing Vocals - Low Register, Subtle Response]
(Мы не одни.)
(Горят огни.)

[Instrumental Break - Epic Cello, Brass, Electric Guitar, Rising Drums, Heavy Orchestral Peak]
[SFX: Distant car passing]

[Bridge - Intimate Deep Male Spoken Rap, Piano, Drums Drop Out]
Слышишь, стихает шум ночных дорог.
Мы у черты, но это не итог.
Пускай исчезнут прошлые следы,
Мы сохраним тепло среди воды.

[Final Chorus - Powerful Baritone, Four LOW Male Backing Harmonies, Epic Strings]
Пока горят огни — мы не одни,
Навстречу утру нас ведут они.
Сквозь этот дождь, сквозь холод и туман,
Найдём свой берег, выйдем к берегам.
[Male Backing Vocals - Close Warm Response]
(Мы не одни.)
(Горят огни.)

[Outro - Solo Piano, Resolving Chord, Long Natural Reverb Tail]
И новый день встречает нас вдали.""",
 "duration":112,"bpm":90,"two_versions":True,
 "use_voice":False,"instrumental":False,"mode":"new","vocal_language":"auto"
}
h=S.get(URL+"/api/health",timeout=7).json()
if h["job"]["status"] in ("preparing","generating","converting") or any(h.get(k,{}).get("active") for k in ("training32","training41","training23")):
 print("QA36_ABORTED_BUSY",h["job"]["status"]);sys.exit(2)
prep=S.post(URL+"/api/prepare",json=song,timeout=30)
print("PREPARE_STATUS",prep.status_code,flush=True)
if prep.status_code!=200:
 print(prep.text[:1400]);sys.exit(1)
x=prep.json()
print("STYLES",x["caption_length"],"LYRIC_CHARS",len(x["lyrics"]),"PLAN",json.dumps(x["structure_plan"],ensure_ascii=True),flush=True)
print("SFX",json.dumps([(f["effect"],f["supported"]) for f in x["effects_plan"]],ensure_ascii=True),flush=True)
assert all(e["supported"] for e in x["effects_plan"])
assert x["caption_length"]<=512 and len(x["lyrics"])<=4096
print("ORIGINAL_WORDS_OK",all(p in x["lyrics"] for p in ("Пока горят огни","Слышишь, стихает","И новый день")),flush=True)
path=Path.home()/"Music Studio"/"Diagnostics"/"QA36";path.mkdir(parents=True,exist_ok=True)
(path/"new_song_request.json").write_text(json.dumps(song,ensure_ascii=False,indent=2),encoding="utf-8")
(path/"prepare_response.json").write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
response=S.post(URL+"/api/generate",json=song,timeout=35)
print("SUBMIT",response.status_code,response.text[:700],flush=True)
assert response.status_code==202,"Generation request failed"

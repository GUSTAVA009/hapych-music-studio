"""Small direct live Music Studio smoke test, one 65-second non-personal take."""
import requests,sys,json
s=requests.Session();s.trust_env=False
BASE="http://127.0.0.1:7870"
song={
 "title":"QA34 - Городские огни",
 "style":"Dark cinematic Russian pop-rap, native Russian male baritone lead, 4 male backing voices harmonize chorus and call-response, clean piano, warm cello strings, smoky saxophone, tight 808 sub bass, wide spacious stereo, clear consonants, 92 BPM, D minor, 65 seconds, instrumental intro, resolved outro",
 "lyrics":"[Intro - Dark Piano, Strings]\n[SFX: Light rain on asphalt]\n[Verse 1 - Deep Russian Male Rap]\nПо мокрому асфальту светят фонари,\nМы начинаем снова, только не спеши.\nСегодня этот город на одной волне,\nИ тихий голос друга слышится во мне.\n[Pre-Chorus - Rising Strings]\nВетер приносит запах мокрых улиц,\nИ наши мысли снова не уснули.\n[Chorus - Four Male Backing Voices, Warm Harmonies, Call And Response]\nГородские огни, не гасните до утра,\nВсё, что было вчера, отпускаем со двора.\n(Мы идём!)\n(До утра!)\nНовый день впереди, наша музыка жива.\n[Instrumental Break - Saxophone Solo, Piano]\n[SFX: Distant car passing]\n[Final Chorus - Four Male Backing Voices, Deep Bass]\nГородские огни, не гасните до утра,\nНас согреет музыка и простые слова.\n[Outro - Soft Piano, Final Chord]\nНовый рассвет, и ночь уже прошла.",
 "duration":65,"bpm":92,"two_versions":False,
 "use_voice":False,"instrumental":False,"mode":"new","vocal_language":"auto",
}
h=s.get(BASE+"/api/health",timeout=8).json()
if h["job"]["status"] in ("generating","preparing","converting") or any(h.get(p,{}).get("active") for p in ("training41","training32","training23")):
 print("QA34_ABORTED_BUSY",h["job"]["status"]);sys.exit(1)
prep=s.post(BASE+"/api/prepare",json=song,timeout=20)
print("PREPARE",prep.status_code)
if prep.status_code!=200:
 print(prep.text[:1600]);sys.exit(2)
info=prep.json()
print("STRUCTURE",info["structure_plan"])
print("CAPTION",info["caption"][:300])
print("LYRICS_LEN",len(info["lyrics"]),"EFFECTS",[(x["effect"],x["supported"]) for x in info["effects_plan"]])
if len(info["lyrics"])>4096:sys.exit(3)
res=s.post(BASE+"/api/generate",json=song,timeout=20)
print("QA34_GENERATION_SUBMITTED",res.status_code,res.text[:400])
if res.status_code!=202:sys.exit(4)

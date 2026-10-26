import requests,json
s=requests.Session();s.trust_env=False
base="http://127.0.0.1:7870"
data={"title":"QA33 — ночной город","style":"Russian deep male baritone rap, native Russian pronunciation, clear full syllables, dark cinematic piano, cello low strings, controlled 808 bass, boom bap drums, wide stereo ambience, 92 BPM, D minor, compact 40-second arrangement","lyrics":"[Intro - Spoken Male Voice]\nГород не спит, дождь на стекле.\n[SFX: Heavy rain on asphalt]\n[SFX: Phone ringing]\n[Verse 1 - Deep Male Rap]\nНочь за окном, и свет фонарей,\nСлышу шаги среди мокрых аллей.\nДальше дорога, и снова звонок,\nНовый рассвет уже недалёк.\n[SFX: Car engine starts]\n[Chorus - Male Baritone]\nНовый день, новый круг, новый шанс,\nСлышишь, город, мы живём сейчас.\n[Outro - Dark Piano]\n[SFX: Phone vibration]","duration":40,"bpm":92,"two_versions":False,"use_voice":False,"instrumental":False,"mode":"new"}
h=s.get(base+"/api/health",timeout=10).json()
if h["job"]["status"] in ("preparing","generating","converting") or h.get("training41",{}).get("active") or h.get("training32",{}).get("active"):
 print("BUSY_NO_SUBMIT",h["job"]["status"])
else:
 r=s.post(base+"/api/generate",json=data,timeout=20)
 print("SUBMITTED",r.status_code,r.text[:800])

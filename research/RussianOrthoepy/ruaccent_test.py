"""RUAccent offline-after-first-download smoke test in isolated environment."""
from pathlib import Path
import json,time,sys
ROOT=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"
D=ROOT/"models";D.mkdir(exist_ok=True)
from ruaccent import RUAccent
print("RUACCENT_LOADING_TINY",flush=True)
t=time.monotonic()
acc=RUAccent()
acc.load(omograph_model_size="tiny",use_dictionary=True,tiny_mode=False,device="CPU",workdir=str(D))
print("RUACCENT_LOAD_SECONDS",round(time.monotonic()-t,2),flush=True)
sentences=[
 "Мне нужен свет твоих окон.",
 "Ты меня снова найдёшь, когда за окном идёт дождь.",
 "Меня услышишь и поймёшь.",
 "На двери висит замок. Старинный замок стоит на холме.",
 "У неё золотые руки. Они подняли руки вверх.",
]
out={}
for i,s in enumerate(sentences):
 a=acc.process_all(s)
 print("RUACCENT_RESULT",i,json.dumps({"original":s,"accent":a},ensure_ascii=False),flush=True)
 out[str(i)]={"text":s,"accent":a}
(ROOT/"ruaccent_smoke.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf8")
print("RUACCENT_TINY_READY",flush=True)

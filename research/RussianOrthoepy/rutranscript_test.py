"""Test new local, no-network, literary Russian allophone transcriber."""
from pathlib import Path
import json,time
from ru_transcript import RuTranscript
phrases=[
 ("Мне нужен свет твоих окон.",None),
 ("Мне нужен свет твоих окон.","Мн+е н+ужен св+ет тво+их о+кон."),
 ("Меня услышишь и поймёшь.",None),
 ("Меня услышишь и поймёшь.","Мен+я усл+ышишь и поймёшь."),
 ("Ты меня снова найдёшь, когда за окном идёт дождь.",None),
]
report={}
for i,(s,stressed) in enumerate(phrases):
 t=time.monotonic()
 try:
  tr=RuTranscript(s,stressed) if stressed is not None else RuTranscript(s)
  tr.transcribe()
  result={"text":s,"manual_stress":stressed,
   "stressed":tr.get_stressed_text(),
   "phonemes":tr.get_phonemes(save_spaces=True,save_stresses=True),
   "allophones":tr.get_allophones(save_spaces=True,save_stresses=True),
   "seconds":round(time.monotonic()-t,2)}
  report[str(i)]=result
  print("RUTRANSCRIPT_PASS",json.dumps({"id":i,**result},ensure_ascii=False),flush=True)
 except Exception as e:
  result={"text":s,"manual_stress":stressed,"error":repr(e)}
  report[str(i)]=result
  print("RUTRANSCRIPT_FAIL",json.dumps({"id":i,**result},ensure_ascii=False),flush=True)
p=Path.home()/"Music Studio"/"Integrations"/"RussianOrthoepy"/"rutranscript_test.json"
p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")

"""Detect the experimental Voice32 GPU reservation; prevent simultaneous song generation."""
from pathlib import Path
import json,time,psutil
ROOT=Path.home()/"Music Studio"
FILE=ROOT/"Training Runs"/"voice32"/"training_reservation.json"
def status():
 try:
  data=json.loads(FILE.read_text(encoding="utf-8"))
  proc=psutil.Process(int(data["pid"]))
  command=" ".join(proc.cmdline()).lower().replace("\\","/")
  valid=(abs(proc.create_time()-float(data["started"]))<2
         and "train_voice32.py" in command
         and time.time()-float(data["reserved_at"])<5400
         and proc.is_running() and proc.status()!=psutil.STATUS_ZOMBIE)
  return {"active":bool(valid),
          "message":"Проходит экспериментальное обучение персонального голоса. Генерация временно недоступна; треки можно слушать." if valid else "",
          "checkpoint_deployed":False,
          "reservation":str(FILE)}
 except (ValueError,KeyError,OSError,TypeError,psutil.Error):return {"active":False,"message":"","checkpoint_deployed":False}

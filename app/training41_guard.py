"""Read-only status of the Music Studio 4.1 isolated experimental LoRA run."""
from pathlib import Path
import json,psutil,time
ROOT=Path(__file__).resolve().parent.parent
RUN=ROOT/"Training Runs"/"music41"
RESERVATION=RUN/"training_reservation.json"
STATUS=RUN/"training_status.json"
def status():
 try:
  info=json.loads(RESERVATION.read_text(encoding="utf-8"))
  pid=int(info["pid"])
  proc=psutil.Process(pid)
  command=" ".join(proc.cmdline()).lower().replace("\\","/")
  ok=(abs(proc.create_time()-float(info["started"]))<2 and
      "train_music41.py" in command and
      time.time()-float(info["reserved_at"])<86400)
  active=bool(ok and proc.is_running() and proc.status()!=psutil.STATUS_ZOMBIE)
 except (ValueError,KeyError,OSError,psutil.Error,TypeError):
  active=False
 try:progress=json.loads(STATUS.read_text(encoding="utf-8"))
 except (ValueError,OSError):progress={}
 return {"active":active,
         "message":"Идёт экспериментальное обучение музыки. Генерация временно недоступна; сохранённые треки можно слушать." if active else "",
         "stage":progress.get("stage","not_started"),
         "details":progress.get("details",""),
         "step":progress.get("step",0),
         "total":progress.get("total",0),
         "experimental":True,"production_model_changed":False,
         "status_updated":progress.get("updated",""),
         "log_path":str(RUN/"training41.log")}

"""Crash-safe resource reservation for an explicitly requested local training run."""
from pathlib import Path
import json,time
import psutil
ROOT=Path(__file__).resolve().parent.parent
FILE=ROOT/'Training Runs'/'voice23'/'reservation.json'
def status():
 try:
  data=json.loads(FILE.read_text(encoding='utf-8'));proc=psutil.Process(int(data['pid']))
  valid=abs(proc.create_time()-float(data['process_started']))<1 and time.time()-float(data['reserved_at'])<5400
  command=' '.join(proc.cmdline()).lower()
  valid=valid and 'training23_supervisor.py' in command
  return {'active':bool(valid),'message':'Идёт обучение голосового адаптера. Новая генерация временно недоступна; записи и готовые песни доступны.' if valid else ''}
 except (OSError,ValueError,KeyError,psutil.Error):return {'active':False,'message':''}

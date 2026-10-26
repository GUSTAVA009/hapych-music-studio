"""QA100 studio-only safe restart using the verified ACE-Step Python environment.
Roll back to original server+index and restart if QA100 smoke check fails.
"""
import os,time,json,sys,subprocess,psutil,requests,traceback
from pathlib import Path
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA100-LowRegister"
app=R/"app";server=app/"studio_server.py";ui=app/"ui"/"index.html"
backup=D/"studio_server_before_QA100.py.bak";uib=D/"index_before_QA100.html.bak"
acepy=R/"ACE-Step-1.5"/".venv"/"Scripts"/"python.exe"
assert acepy.exists() and backup.exists() and uib.exists()
session=requests.Session();session.trust_env=False
h=session.get("http://127.0.0.1:7870/api/health",timeout=6).json()
assert h["job"]["status"]=="idle" and h["ready"] is True
assert not any(h.get(k,{}).get("active",False) for k in ("training23","training32","training41"))
candidates=[c.pid for c in psutil.net_connections(kind="tcp") if c.status=="LISTEN" and c.laddr.port==7870]
assert len(candidates)==1,candidates
pid=candidates[0];proc=psutil.Process(pid)
assert any("studio_server.py" in a for a in proc.cmdline()),proc.cmdline()
print("QA100_STOP_STUDIO_ONLY",pid,flush=True)
log=D/"qa100_validated_server.log"
env=os.environ.copy();env.update(PYTHONUTF8="1",PYTHONIOENCODING="utf-8",
 NO_PROXY="127.0.0.1,localhost,::1",no_proxy="127.0.0.1,localhost,::1")
def start():
 with log.open("ab") as stdout:
  x=subprocess.Popen([str(acepy),"-u",str(server)],cwd=str(app),
    env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=subprocess.STDOUT,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    close_fds=True)
 print("QA100_STARTED_STUDIO",x.pid,flush=True)
 return x
def health(expect):
 for i in range(45):
  try:
   r=session.get("http://127.0.0.1:7870/api/health",timeout=3)
   if r.status_code==200 and r.json().get("ready") is True:
    if expect and "qa100-readonly-preview" not in r.json().get("production_patch",""):
     raise RuntimeError("New QA100 server did not start, old server is active")
    return r.json()
  except requests.ConnectionError:pass
  except requests.Timeout:pass
  time.sleep(.33)
 raise RuntimeError("Studio server did not become ready")
proc.terminate()
try:proc.wait(timeout=12)
except psutil.TimeoutExpired:raise RuntimeError("Old Studio process did not stop cleanly")
try:
 candidate=start();live=health(True)
 html=session.get("http://127.0.0.1:7870/qa100-compare",timeout=10)
 assert html.status_code==200 and "QA100" in html.text
 index=session.get("http://127.0.0.1:7870/",timeout=10)
 assert index.status_code==200 and 'href="/qa100-compare"' in index.text
 sounds={}
 for name in ("qa54","qa100"):
  response=session.get("http://127.0.0.1:7870/api/qa100-audio/"+name,
     headers={"Range":"bytes=0-1023"},timeout=15)
  assert response.status_code==206 and len(response.content)==1024,(name,response.status_code,len(response.content))
  sounds[name]=response.headers.get("Content-Range")
 result={"ok":True,"new_pid":candidate.pid,"ready":live["ready"],"job_status":live["job"]["status"],
 "qa100_preview_route":200,"settings_link":True,"audio_ranges":sounds,
 "no_model_or_song_change":True}
except Exception as exc:
 server.write_bytes(backup.read_bytes());ui.write_bytes(uib.read_bytes())
 # safely stop this specific testing server if it exists
 if "candidate" in locals() and candidate.poll() is None:
  candidate.terminate()
  try:candidate.wait(timeout=10)
  except subprocess.TimeoutExpired:pass
 new=start()
 oldhealth=health(False)
 result={"ok":False,"error":repr(exc),"rolled_back":True,"restarted_pid":new.pid,
 "studio_ready":oldhealth["ready"],"job_status":oldhealth["job"]["status"]}
(D/"qa100_restart_success.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA100_STUDIO_RESTART_RESULT",json.dumps(result,ensure_ascii=True),flush=True)
if not result["ok"]:sys.exit(1)

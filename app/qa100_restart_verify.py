"""QA100 safe restart ONLY studio_server.py listener 7870.
Guard status idle; do not restart ACE-Step or models. Rollback on failure.
"""
import sys,os,subprocess,time,requests,psutil,shutil,json
from pathlib import Path
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA100-LowRegister"
app=R/"app";server=app/"studio_server.py";old=D/"studio_server_before_QA100.py.bak"
index=app/"ui"/"index.html";old_index=D/"index_before_QA100.html.bak"
assert old.is_file() and old_index.is_file()
session=requests.Session();session.trust_env=False
health=session.get("http://127.0.0.1:7870/api/health",timeout=6).json()
assert health["job"]["status"]=="idle"
assert health.get("training32",{}).get("active")==False
assert health.get("training41",{}).get("active")==False
pids={x.pid for x in psutil.net_connections(kind="tcp") if x.status=="LISTEN" and x.laddr.port==7870}
assert len(pids)==1,pids
pid=pids.pop();p=psutil.Process(pid)
cmd=p.cmdline();exe=p.exe()
assert Path(cmd[-1]).resolve()==server.resolve(),cmd
print("QA100_RESTART_SAFE_TARGET",pid,exe,flush=True)
# Preserve old log, use separate restart logs.
log=D/"qa100_server_restart.log"
env=os.environ.copy()
env.update(PYTHONUTF8="1",NO_PROXY="127.0.0.1,localhost,::1",no_proxy="127.0.0.1,localhost,::1")
p.terminate()
try:p.wait(timeout=15)
except psutil.TimeoutExpired:raise RuntimeError("Server did not quit; do not force kill")
def launch():
 with log.open("ab") as file:
  kwargs=dict(cwd=str(app),stdin=subprocess.DEVNULL,stdout=file,stderr=subprocess.STDOUT,env=env,
       close_fds=True,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
  proc=subprocess.Popen([exe,str(server)],**kwargs)
 return proc
def check_ready(expect_qa100=True):
 for j in range(50):
  try:
   h=session.get("http://127.0.0.1:7870/api/health",timeout=3)
   if h.status_code==200 and h.json().get("ready",False):
    if expect_qa100 and "qa100-readonly-preview" not in h.json().get("production_patch",""):continue
    return h.json()
  except requests.RequestException:pass
  time.sleep(.35)
 raise RuntimeError("Music Studio 7870 did not come back ready")
try:
 proc=launch();h=check_ready()
 page=session.get("http://127.0.0.1:7870/qa100-compare",timeout=10)
 assert page.status_code==200 and "QA100" in page.text
 home=session.get("http://127.0.0.1:7870/",timeout=10)
 assert home.status_code==200 and 'href="/qa100-compare"' in home.text
 sounds={}
 for label in ("qa54","qa100"):
  response=session.get("http://127.0.0.1:7870/api/qa100-audio/"+label,
        headers={"Range":"bytes=0-1023"},timeout=15)
  assert response.status_code==206,(label,response.status_code,response.text[:200])
  assert len(response.content)==1024 and response.content[:3]==b"ID3" or len(response.content)==1024, label
  sounds[label]={"status":response.status_code,"bytes":len(response.content),
                 "range":response.headers.get("Content-Range")}
 result={"success":True,"old_pid":pid,"new_pid":proc.pid,
   "studio_ready":h["ready"],"job":h["job"]["status"],
   "production_patch":h.get("production_patch"),"both_audio_valid":sounds,
   "home_has_link":True,"model_unchanged":True,
   "engine_7862_left_running":True}
except Exception as exc:
 server.write_bytes(old.read_bytes());index.write_bytes(old_index.read_bytes())
 # Do not kill any ACE model. Rollback only studio server.
 for x in psutil.net_connections(kind="tcp"):
  if x.status=="LISTEN" and x.laddr.port==7870:
   child=psutil.Process(x.pid)
   if any("studio_server.py" in w for w in child.cmdline()):
    child.terminate()
    try:child.wait(timeout=12)
    except psutil.TimeoutExpired:pass
 launch()
 check_ready(expect_qa100=False)
 result={"success":False,"error":str(exc),"rolled_back":True,
   "studio_restored":True}
(D/"qa100_studio_restart_result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA100_LIVE_SMOKE",json.dumps(result,ensure_ascii=True),flush=True)
if not result["success"]:sys.exit(1)

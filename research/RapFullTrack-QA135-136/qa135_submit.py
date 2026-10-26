from pathlib import Path
import requests,json,sys,time
sys.stdout.reconfigure(encoding="utf8")
P=Path.home()/"Music Studio"/"Integrations"/"RapFullTrack-QA135"
result=P/"QA135_submit_result.json"
if result.exists():
 saved=json.loads(result.read_text(encoding="utf8"))
 if saved.get("ok") and saved.get("id"):raise RuntimeError("Already submitted; refusing duplicate generation: "+saved["id"])
req=json.loads((P/"QA135_rap_request.json").read_text(encoding="utf8"))
assert len(req["lyrics"])>800 and req["duration"]==150 and req["bpm"]==100
assert req["apply_voice"] is False and req["use_voice"] is True
s=requests.Session();s.trust_env=False
url="http://127.0.0.1:7870"
h=s.get(url+"/api/health",timeout=7).json()
if h["job"]["status"] in ("preparing","generating","converting"):raise RuntimeError("Studio already working: "+h["job"]["status"])
reply=s.post(url+"/api/generate",json=req,timeout=28)
print("QA135_SUBMIT_HTTP",reply.status_code,flush=True)
data=reply.json()
if reply.status_code!=202:
 result.write_text(json.dumps({"ok":False,"error":data},ensure_ascii=False,indent=2),encoding="utf8")
 raise RuntimeError("Generation refused: "+str(data)[:1000])
assert data["ok"] and data["id"]
out={"ok":True,"id":data["id"],"request_duration":150,
 "title":req["title"],"selected_voice_preset":"QA133_ConsonantProtection_ApexSVC",
 "studio_generation_voice_mode":"reference_for_register_only; Apex vocal-only conversion after generation",
 "status":"generation_submitted","started":time.strftime("%Y-%m-%d %H:%M:%S")}
result.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
print("QA135_STUDIO_JOB",data["id"],flush=True)

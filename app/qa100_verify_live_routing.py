"""Real Music Studio API /api/prepare route smoke tests, no generation."""
from pathlib import Path
import requests,json,sys
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA100-LowRegister";D.mkdir(exist_ok=True,parents=True)
sys.path.insert(0,str(R/"app"))
import voice_profiles34
s=requests.Session();s.trust_env=False
results=[]
for match,profile in [
("QA76_low_legato","artist_cd95ce73315a47e9a819"),
("3867cb",""),
("65f5f3","")]:
 voices=list((R/"Мой голос").glob("*"+match+"*.wav"))
 assert len(voices)==1,voices
 f=voices[0]
 req={"title":"QA100 Prepare Only","style":"Soft native Russian male baritone legato, piano, gentle rhythm, 85 BPM. No robotic stutters.","lyrics":"[Verse]\nТепло и свет. Дороги.\n[Chorus]\nПускай любовь горит.\n[End]","duration":35,"bpm":85,"two_versions":False,"use_voice":True,"voice":f.name,"voice_profile_id":profile}
 reply=s.post("http://127.0.0.1:7870/api/prepare",json=req,timeout=25)
 result={"reference_suffix":match,"http":reply.status_code}
 try:
  doc=reply.json()
  result.update(model=doc.get("voice_model_preview",{}).get("model"),trained=doc.get("voice_model_preview",{}).get("trained"),
                warning=doc.get("voice_model_preview",{}).get("warning"),
                error=doc.get("error"),caption=doc.get("caption"))
 except Exception as exc:result["json_error"]=str(exc)
 results.append(result)
 print("QA100_REAL_PREPARE",json.dumps(result,ensure_ascii=True)[:1500],flush=True)
assert results[0]["http"]==200 and results[0]["trained"] is True
assert results[1]["http"]==200 and results[1]["trained"] is True
assert results[2]["http"]==200 and results[2]["trained"] is False
(D/"qa100_live_api_voice_selection.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA100_REAL_STUDIO_API_VOICE_ROUTE_VERIFIED",flush=True)

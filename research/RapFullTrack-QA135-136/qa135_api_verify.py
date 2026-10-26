from pathlib import Path
import json,requests,urllib.parse,sys
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
r=json.loads((D/"QA135_final_report.json").read_text(encoding="utf8"))
p=Path(r["library_mp3"])
s=requests.Session();s.trust_env=False
url="http://127.0.0.1:7870"
lib=s.get(url+"/api/tracks",timeout=12)
assert lib.status_code==200
tracks=lib.json()["tracks"]
matches=[x for x in tracks if x.get("name")==p.name]
assert len(matches)==1,(len(matches),p.name)
play=url+"/api/audio/"+urllib.parse.quote(p.name,safe="")
resp=s.get(play,stream=True,timeout=15)
assert resp.status_code==200,resp.status_code
assert resp.headers.get("Content-Type","").startswith(("audio/","application/octet-stream")),resp.headers
assert int(resp.headers.get("Content-Length","0"))==p.stat().st_size
resp.close()
details=s.get(url+"/api/track_details",params={"name":p.name},timeout=12)
assert details.status_code==200
cover=s.get(url+"/api/cover_status",params={"name":p.name},timeout=12)
assert cover.status_code==200
report={
 "studio_library_contains_new_voice_track":True,
 "mp3_is_streamed_by_studio":True,
 "playback_url":play,
 "voice_track":p.name,
 "list_entry":matches[0],
 "details_status":details.status_code,
 "cover_status":cover.json(),
}
(D/"QA135_api_verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("QA135_LIBRARY_CONFIRMED",p.name,flush=True)
print("QA135_STREAM_URL",play,flush=True)
print("QA135_COVER",json.dumps(cover.json(),ensure_ascii=False)[:350],flush=True)

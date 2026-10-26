from pathlib import Path
import json,requests,soundfile as sf,hashlib,sys
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
state=json.loads((D/"QA135_submit_result.json").read_text(encoding="utf8"))
s=requests.Session();s.trust_env=False
h=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["id"]==state["id"]
assert h["job"]["status"]=="done",h["job"]["status"]
files=h["job"]["files"];assert len(files)==1,len(files)
name=files[0]["name"]
assert name.endswith(".mp3")
song=R/"Мои треки"/name
meta=song.with_suffix(".track.json")
assert song.is_file() and meta.is_file()
details=json.loads(meta.read_text(encoding="utf8"))
assert "rap" in details["style_original"].lower()
assert not details.get("voice_applied",False)
assert details["lyrics_original"]==json.loads((D/"QA135_rap_request.json").read_text(encoding="utf8"))["lyrics"]
assert details.get("voice_model_used") is None or details.get("voice_applied") is False
master=R/"Мастер WAV"/(song.stem+".wav")
assert master.is_file()
info=sf.info(master)
assert 140<info.duration<153,(info.duration,master)
report={"status":"music_studio_rap_source_created","studio_job":state["id"],
 "title":details["title"],"file_mp3":str(song),"file_master_wav":str(master),
 "duration_sec":round(info.duration,3),
 "samplerate":info.samplerate,"channels":info.channels,
 "master_sha256":hashlib.sha256(master.read_bytes()).hexdigest(),
 "mp3_sha256":hashlib.sha256(song.read_bytes()).hexdigest(),
 "lyrics_verified_identical":True,"source_voice_transferred":False,
 "studio_style":details["style_original"],
 "source_is_untouched":True}
(D/"QA135_rap_source_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("QA135_RAP_SONG_READY",report["title"],report["duration_sec"],flush=True)
print("QA135_MASTER",str(master),flush=True)
print("QA135_MP3",str(song),flush=True)

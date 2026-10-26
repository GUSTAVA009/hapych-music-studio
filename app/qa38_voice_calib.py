"""QA38: transfer selected native-voice reference to 40-second controlled song cut.
No personal contaminated checkpoints, no modifications to main library.
"""
from pathlib import Path
import requests,time,json,subprocess,sys
ROOT=Path.home()/"Music Studio";sys.path.insert(0,str(ROOT/"app"))
from voice_bridge25 import convert_song
D=ROOT/"Diagnostics"/"QA38";D.mkdir(exist_ok=True,parents=True)
raws=sorted((ROOT/"Исходные версии").glob("*QA38*_1.wav"))
assert len(raws)==1,raws
ref=next((ROOT/"Мой голос").glob("*df413d.wav"),None)
assert ref and ref.is_file()
assert not (ROOT/"Voice Engine"/"seed-vc"/"runs"/"music_studio_personal_v1"/"ft_model.pth").exists()
s=requests.Session();s.trust_env=False
h=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("preparing","generating","converting")
assert not any(h.get(k,{}).get("active") for k in ("training32","training41","training23"))
cut=D/"QA38_Source_8to48.wav"
cmd=["ffmpeg","-v","error","-nostdin","-y","-ss","8","-i",str(raws[0]),"-t","40",
     "-ac","2","-ar","44100","-c:a","pcm_s24le",str(cut)]
subprocess.run(cmd,check=True,capture_output=True,timeout=60)
dest=D/"QA38_PersonalVoice_40s.mp3"
beg=time.monotonic()
convert_song(cut,ref,dest,steps=40,trained=False,
   register_mode="original",vocal_language="ru",chorus_ranges=[],
   on_stage=lambda z:print("VOICE_STAGE",z,flush=True))
q=json.loads(dest.with_suffix(".quality.json").read_text(encoding="utf-8"))
result={"status":q["voice_check"]["status"],"voice_check":q["voice_check"]["metrics"],
 "pitch_consistency":q.get("pitch_consistency",{}).get("status"),
 "cosine":q.get("speaker_embedding_cosine"),"ref":ref.name,
 "duration":40,"full_song_published":False,"elapsed_seconds":round(time.monotonic()-beg,2)}
(D/"personal_voice_calibration.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA38_40S_CALIBRATION",json.dumps(result,ensure_ascii=True),flush=True)

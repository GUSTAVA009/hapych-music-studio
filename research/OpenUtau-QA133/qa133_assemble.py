"""QA133 assemble exact DiffSinger CPU phrase renders into auditable WAV/MP3.
Do not mix source singer audio with original owner's voice. Keep all
audio unprocessed beyond alignment and standard MP3 encoding.
"""
from pathlib import Path
import os,json,hashlib,subprocess,re,sys
import soundfile as sf,numpy as np
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
QA132=R/"QA132-KogdaPronunciation"
D=QA132/"QA133-FinalDiction"
source=R/"QA129_Score"/"QA129_real_singing_report.json"
base=json.loads(source.read_text(encoding="utf8"))
prior=json.loads((QA132/"QA133-FinalDiction"/"QA133_manifest.json").read_text(encoding="utf8"))
assert hashlib.sha256((QA132/"QA132_Keiro_RussianCaseGuard.ustx").read_bytes()).hexdigest()==prior["base_sha256"]
assert len(base["stems"])==4
duration=base["duration"]
sr=base["samplerate"]
results={}
for tag in prior["cases"]:
 path=D/tag
 cache=path/"Data"/"Cache"
 log=(path/"qa133_render_stdout.txt").read_text(encoding="utf-8")
 assert "QA132_RENDER_COMPLETE" in log
 lines=[re.search(rf"QA132_PHRASE_{n}_PHONEMES=(.*)",log).group(1).strip().split() for n in range(1,5)]
 assert lines[2][:5]==["ru/k","ru/A","ru/g","ru/d","ru/a"],(tag,lines[2][:5])
 assert lines[3][7:11]==["ru/m","ru/A","ru/j","ru/u"],(tag,lines[3][7:11])
 if tag.startswith("A_"):assert lines[2][-4:]==["ru/d","ru/o","ru/sh","ru/tj"]
 else:assert lines[2][-3:]==["ru/d","ru/o","ru/shj"]
 wavs=sorted(cache.glob("ds-*.wav"),key=lambda p:p.stat().st_mtime)
 assert len(wavs)==4
 x=np.zeros(round(duration*sr),dtype=np.float64)
 stem_details=[]
 for part,(base_stem,wav) in enumerate(zip(base["stems"],wavs)):
  y,fs=sf.read(wav,always_2d=True,dtype="float32")
  assert fs==sr and np.isfinite(y).all() and y.shape[1] in (1,2)
  y=y.mean(axis=1).astype("float64")
  assert abs(len(y)/sr-base_stem["cached_audio_sec"])<.06,(tag,part,len(y)/sr,base_stem)
  onset=round(base_stem["onset_sec"]*sr)
  end=min(len(x),onset+len(y))
  x[onset:end]+=y[:end-onset]
  stem_details.append({"line":part+1,"cache_name":wav.name,
      "start":base_stem["onset_sec"],"duration":round(len(y)/sr,3),
      "sha256":hashlib.sha256(wav.read_bytes()).hexdigest()})
 assert np.max(np.abs(x))<0.99
 name=tag.replace("_","-")
 wavout=D/(f"QA133_{name}_Keiro_21s.wav")
 mp3out=wavout.with_suffix(".mp3")
 sf.write(wavout,x.astype("float32"),sr,subtype="PCM_24")
 proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wavout),
    "-c:a","libmp3lame","-b:a","192k",str(mp3out)],capture_output=True,text=True,timeout=40)
 assert proc.returncode==0,proc.stderr
 assert abs(sf.info(wavout).duration-duration)<.01
 results[tag]={"wav":str(wavout),"mp3":str(mp3out),"stems":stem_details,
   "phonemes":[{"line":i+1,"phones":p} for i,p in enumerate(lines)],
   "duration":sf.info(wavout).duration,
   "peak":round(float(np.max(abs(x))),5),
   "rms":round(float(np.sqrt(np.mean(x*x))),5),
   "sha256":hashlib.sha256(wavout.read_bytes()).hexdigest()}
 print("QA133_WAVE_READY",tag,results[tag]["duration"],mp3out,flush=True)
report={"status":"two_acoustic_candidates_assembled",
        "license":"Keiro LUNAI Project noncommercial research only",
        "original_mic_untouched":True,"working_studio_untouched":True,
        "no_voice_training":True,"render_device":"CPU","cases":results}
(D/"QA133_render_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")

"""Recover four locally rendered OpenUtau DiffSinger phrase WAVs into isolated QA129 audio.
This is a noncommercial diction test using Keiro Revenant from LUNAI Project.
No voice-model training, no voice-conversion, no change to Music Studio.
"""
from pathlib import Path
import json,sys,hashlib,math,subprocess,collections
import soundfile as sf
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
D=ROOT/"QA129_Score"
SRC=ROOT/"lunai_portable"/"Cache"
meta=json.loads((D/"QA129_phones.json").read_text(encoding="utf-8"))
assert meta["notes"]==31 and meta["lines"]==4
candidates=sorted(SRC.glob("ds-*-depth0.60-steps20.wav"),key=lambda p:p.stat().st_mtime)
assert len(candidates)==4, ("Unexpected number of cached clips, will not guess",len(candidates))
sr=44100;bpm=102;res=480
def seconds(ticks):return ticks*60/(bpm*res)
groups=collections.defaultdict(list)
for s in meta["syllables"]:groups[s["line"]].append(s)
assert len(groups)==4
timeline=np.zeros((round(meta["duration_sec"]*sr)+sr,1),dtype="float64")
records=[]
for i,p in enumerate(candidates,1):
 expected=groups[i]
 start_sec=seconds(expected[0]["tick"])
 end_sec=seconds(expected[-1]["tick"]+expected[-1]["duration_ticks"])
 segment,s=sf.read(p,always_2d=True,dtype="float32")
 assert s==sr
 assert segment.shape[1] in (1,2)
 segment=segment.mean(axis=1).astype("float64")
 actual=len(segment)/sr
 expected_len=end_sec-start_sec
 assert 0.20<actual-expected_len<0.55,(i,actual,expected_len)
 assert np.isfinite(segment).all()
 onset=round(start_sec*sr)
 end=onset+len(segment)
 assert end<=len(timeline)
 timeline[onset:end,0]+=segment
 records.append({"line":i,"cache_file":p.name,"expected_phrase_sec":round(expected_len,3),
  "cached_audio_sec":round(actual,3),"onset_sec":round(start_sec,3),
  "sample_peak":round(float(np.max(np.abs(segment))),4),
  "sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
out=D/"QA129_Keiro_Russian_RealSinging_21s.wav"
y=timeline[:int(meta["duration_sec"]*sr),0]
assert len(y)>sr*19
assert np.max(np.abs(y))<0.98
sf.write(out,y.astype("float32"),sr,subtype="PCM_24")
wavinfo=sf.info(out)
mp3=D/"QA129_Keiro_Russian_RealSinging_21s.mp3"
proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y",
 "-i",str(out),"-codec:a","libmp3lame","-b:a","192k",str(mp3)],
 capture_output=True,text=True,timeout=45)
assert proc.returncode==0,proc.stderr
report={
 "status":"four_sung_fragments_merged","provenance":"Keiro Revenant v170 from LUNAI Project; isolated noncommercial QA",
 "model":"DiffSinger LUNAI 170 with bundled TGM HiFiGAN vocoder",
 "input_project":"QA129_Keiro_RussianDiffSinger.ustx",
 "wav":str(out),"mp3":str(mp3),"duration":round(wavinfo.duration,3),
 "samplerate":sr,"wav_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "rms":round(float(np.sqrt(np.mean(y*y))),6),
 "peak":round(float(np.max(abs(y))),5),
 "asr_verified":False,
 "syllable_stress_human_verified":False,
 "human_timbre_verified":False,
 "is_owners_voice":False,
 "project_singer_license":"Noncommercial testing only; attribution: Keiro Revenant from LUNAI Project",
 "isolation":{"production_studio_modified":False,"owner_mic_untouched":True,
  "third_party_voice_used_to_train_model":False},
 "stems":records
}
(D/"QA129_real_singing_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA129_REAL_SINGING_WAV_READY",round(wavinfo.duration,3),len(candidates),round(report["rms"],5),round(report["peak"],5),flush=True)
print(out,flush=True)
print(mp3,flush=True)

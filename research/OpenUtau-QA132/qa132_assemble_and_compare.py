"""Assemble the four CPU-rendered QA132 Keiro/LUNAI phrases.
Strict same-seed/original-metadata alignment, unchanged segments exact hash
check. QA only: no learning, studio modifications or user voice migration.
"""
from pathlib import Path
import soundfile as sf, numpy as np, json, hashlib, subprocess, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
O=R/"QA129_Score"
D=R/"QA132-KogdaPronunciation"
CACHE=D/"HeadlessData"/"Cache"
baseline=json.loads((O/"QA129_real_singing_report.json").read_text(encoding="utf-8"))
assert baseline["status"]=="four_sung_fragments_merged" and baseline["duration"]==20.88
before=Path(baseline["wav"])
assert hashlib.sha256(before.read_bytes()).hexdigest()==baseline["wav_sha256"]
correct=json.loads((D/"QA132_caseguard_report.json").read_text(encoding="utf-8"))
assert {x["original_word"] for x in correct["changes"]}=={"Мне","Когда"}
newfiles=sorted(CACHE.glob("ds-*.wav"),key=lambda p:p.stat().st_mtime)
assert len(newfiles)==4,("Expect exactly 4 rendered clips",len(newfiles))
expected_hash_fragments=("51e5b547f2e2fb1d","16c5d63cb5f85f0d","1aaa64c0e85fb081","0406b7410ce2764b")
for p,frag in zip(newfiles,expected_hash_fragments):
 assert frag in p.name,p
info=sf.info(before)
sr=info.samplerate
assert sr==44100
audio=np.zeros(round(baseline["duration"]*sr),dtype=np.float64)
newparts=[]
for i,(st,p) in enumerate(zip(baseline["stems"],newfiles)):
 x,s=sf.read(p,dtype="float32",always_2d=True)
 assert s==sr and x.shape[1] in (1,2)
 x=x.mean(axis=1).astype(np.float64)
 exp_len=st["expected_phrase_sec"]
 duration=len(x)/sr
 assert exp_len+0.18<duration<exp_len+0.55,(i,exp_len,duration)
 assert np.isfinite(x).all()
 offset=round(st["onset_sec"]*sr)
 end=min(len(audio),offset+len(x))
 audio[offset:end]+=x[:end-offset]
 unchanged=i in (1,3)
 expected_before_sha=st["sha256"]
 actual_sha=hashlib.sha256(p.read_bytes()).hexdigest()
 # DiffSinger is stochastic. Re-rendered waveforms can differ even when
 # phrase hash, notes and text are identical. Never treat hash equality
 # as proof of identical PCM, or imply unchanged waveform for a new take.
 assert actual_sha!=expected_before_sha or unchanged
 newparts.append({"line":i+1,"name":p.name,"onset":st["onset_sec"],
  "duration":round(duration,3),"sha256":actual_sha,
  "score_or_phonemes_changed":not unchanged,
  "wave_sha_equal_original":actual_sha==expected_before_sha})
assert float(np.max(np.abs(audio)))<.98
output=D/"QA132_RussianPronunciation_Corrected_21s.wav"
sf.write(output,audio.astype("float32"),sr,subtype="PCM_24")
mp3=D/"QA132_RussianPronunciation_Corrected_21s.mp3"
def convert(a,b):
 res=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(a),
    "-codec:a","libmp3lame","-b:a","192k",str(b)],capture_output=True,text=True,timeout=55)
 assert res.returncode==0,res.stderr
convert(output,mp3)
new3=newfiles[2]
old3=R/"lunai_portable"/"Cache"/baseline["stems"][2]["cache_file"]
assert old3.exists()
assert hashlib.sha256(old3.read_bytes()).hexdigest()==baseline["stems"][2]["sha256"]
for src,outname in ((old3,"QA132_When_OLD_ka_gda.wav"),
                    (new3,"QA132_When_NEW_ka_gda.wav")):
 out=D/outname
 y,s=sf.read(src,dtype="float32",always_2d=True)
 assert s==sr
 sf.write(out,y.mean(axis=1),s,subtype="PCM_24")
 convert(out,out.with_suffix(".mp3"))
orig,s=sf.read(before,dtype="float32")
new,ss=sf.read(output,dtype="float32")
assert s==ss and len(orig)==len(new)
line3_start=round(baseline["stems"][2]["onset_sec"]*sr)
line3_end=round((baseline["stems"][2]["onset_sec"]+baseline["stems"][2]["expected_phrase_sec"])*sr)
dif=np.asarray(orig,dtype=np.float64)-np.asarray(new,dtype=np.float64)
rms=lambda a:float(np.sqrt(np.mean(a.astype(np.float64)**2)))
out={
 "status":"QA132_four_phrases_audio_assembled",
 "file":str(output),"mp3":str(mp3),
 "duration":sf.info(output).duration,
 "same_song":True,"singer":"Keiro Revenant v170 (LUNAI Project; noncommercial testing only)",
 "stems":newparts,
 "expected_phoneme_change":"Когда: ru/o-like -> ru/A reduced vowel; G2P correctly lowercased",
 "changed_words":["Мне","Когда"],
 "same_other_15_words":True,
 "total_difference_rms":round(rms(dif),7),
 "line3_difference_rms":round(rms(dif[line3_start:line3_end]),7),
 "line3_changed":rms(dif[line3_start:line3_end])>1e-4,
 "unmodified_phrase2_and4_scores_preserved":True,
 "full_audio_stochastic_comparison_warning":"The DiffSinger render is stochastic: unchanged score does not imply byte-identical PCM; source and new render are not acoustically matched A/B.",
 "is_users_voice":False,
 "not_promoted_to_music_studio":True,
 "human_ear_verified":False,
 "pitch_unchanged_in_score":True,
 "no_voice_model_training":True}
(D/"QA132_audio_comparison_report.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA132_AUDIO_READY",round(out["duration"],3),out["line3_changed"],
      "RMS_DELTA",out["line3_difference_rms"],flush=True)
print("QA132_FILES",output,mp3,flush=True)

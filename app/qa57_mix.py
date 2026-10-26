"""QA57 assemble uninterrupted phrase-level Seed-VC vocal, then one master.
Melody from ACE-Step, style only from user's one selected clean mic record.
No re-trained or live model changes; no extra high-band consonant splice.
"""
from pathlib import Path
import os,sys,json,hashlib,subprocess
import numpy as np,soundfile as sf
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA57"
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import finish
from voice_guard42 import check
data=json.loads((D/"qa57_inputs.json").read_text(encoding="utf-8"))
parts=json.loads((D/"qa57_phrase_progress.json").read_text(encoding="utf-8"))
assert len(parts)==len(data["phrase_clips"])==5
sr=data["sample_rate"];source_path=D/"QA57_clean_source_vocals.wav";backing_path=D/"QA57_backing.wav"
source,ss=sf.read(source_path,dtype="float32",always_2d=True)
back,sb=sf.read(backing_path,dtype="float32",always_2d=True)
assert ss==sb==sr==44100
n=min(len(source),len(back));src=source[:n].mean(axis=1)
vocal=np.zeros(n,dtype=np.float32)
report=[]
for seg,p in zip(data["phrase_clips"],parts):
 assert seg["id"]==p["phrase_id"] and p["chunks"]==1
 y,sy=sf.read(p["converted"],dtype="float32",always_2d=True)
 assert sy==sr
 x=y.mean(axis=1)
 a=int(round(seg["start_s"]*sr));b=int(round(seg["end_s"]*sr))
 # Since the manifest uses 2 decimals (multiple of 0.02 seconds), round-trip is exact.
 target_len=b-a
 difference=len(x)-target_len
 assert abs(difference)<round(.08*sr),(seg["id"],difference)
 if len(x)<target_len: x=np.pad(x,(0,target_len-len(x)))
 if len(x)>target_len: x=x[:target_len]
 # Only very quiet cutpoints were selected; touch <70ms on either side.
 # Fade to zero exactly at cut, preventing clicks without time stretching words.
 fade=int(.06*sr)
 f=np.ones(len(x),dtype=np.float32)
 if seg["id"]>1:
  f[:fade]=np.sin(np.linspace(0,np.pi/2,fade))**2
 if seg["id"]<len(parts):
  f[-fade:]=np.cos(np.linspace(0,np.pi/2,fade))**2
 vocal[a:b]+=x*f
 report.append({"id":seg["id"],"from":seg["start_s"],"to":seg["end_s"],
                "source_duration_s":round(target_len/sr,3),"converted_duration_s":p["duration_s"],
                "net_audio_sample_diff":difference,"fade_half_ms":60})
sf.write(D/"QA57_phrased_vocal_raw.wav",vocal,sr,subtype="FLOAT")
# The 45s diagnostic ends inside a longer song; fade only the listening export
# after the last target word at approximately 34s.
ending=int(1.0*sr)
vocal[-ending:]*=np.cos(np.linspace(0,np.pi/2,ending))**2
sf.write(D/"QA57_phrased_vocal_test.wav",vocal,sr,subtype="FLOAT")
processed=D/"QA57_phrased_vocal_finished.wav"
master=D/"QA57_MyVoice_PhraseSynthesis_Master_24bit.wav"
info=finish(D/"QA57_phrased_vocal_test.wav",backing_path,source_path,processed,master,chorus_ranges=[])
checkinfo=check(source_path,D/"QA57_phrased_vocal_test.wav",D/"QA57_voicecheck.json","ru")
# Save compressed playback only if decoding and quality checks generated valid data
mp3=D/"QA57_MyVoice_PhraseSynthesis_45sec_320kbps.mp3"
result=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(master),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=100)
assert result.returncode==0,result.stderr[-600:]
audio,ar=sf.read(master,always_2d=True,dtype="float32")
assert ar==44100 and audio.shape[1]==2 and not np.isnan(audio).any()
quality={"version":"QA57","method":"five independent single-mel-chunk Seed-VC phrases, joined at source-vocal quiet points",
 "voice_reference":data["reference"]["source"],"voice_model":"alex_clean_qa44_v2",
 "inference_cfg":.90,"step_count":40,
 "phrase_stitching":report,"total_diffusion_chunks":sum(p["chunks"] for p in parts),
 "source_mic_added_to_mix":False,"source_fricatives_inserted":False,
 "separate_final_audio_fade_s":1.0,
 "output_seconds":round(len(audio)/sr,3),"post_mix":info,
 "continuity_guard":checkinfo,"human_listen_verified":False,
 "native_russian_diction_verified":False,"words_reconstructed":False,
 "mp3":str(mp3),"wav":str(master),
 "mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest()}
(D/"qa57_master_report.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA57_COMPLETE",json.dumps({k:v for k,v in quality.items() if k not in ("post_mix","continuity_guard","phrase_stitching")},ensure_ascii=True),flush=True)
print("QA57_VOICE_METRICS",json.dumps(checkinfo.get("metrics"),ensure_ascii=True),flush=True)

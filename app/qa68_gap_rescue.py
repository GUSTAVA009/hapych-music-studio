"""QA68 selective voiced syllable support.
Keep most QA54 personal converted signal unchanged (protect the owner's timbre).
When source has intact syllables but QA54 vocal drops >6-12dB, crossfade only
those brief missing sounds from continuous source-phase spectral-tone carrier QA67.
Never splice a different person's actual recording: carrier is the original ACE
generated lead colored by QA54 averaged timbre. This is NOT full voice cloning.
Test-only, no production changes.
"""
from pathlib import Path
import json,hashlib,subprocess,sys
import numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA68";D.mkdir(parents=True,exist_ok=True)
Q=R/"Diagnostics"/"QA54"
source,sr=sf.read(Q/"QA54_CFG090_35s.source.wav",dtype="float32",always_2d=True)
converted,rs=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
carrier,cr=sf.read(R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",dtype="float32",always_2d=True)
assert sr==rs==cr==44100
x=source.mean(axis=1);y=converted.mean(axis=1);z=carrier.mean(axis=1)
assert len(x)==len(y)==len(z)
N=len(x);hop=round(sr*.01)
from scipy.signal import fftconvolve
def envelope(signal):
 squares=signal.astype(np.float64)**2
 filtered=gaussian_filter1d(squares,sigma=sr*.013,mode="reflect")[::hop]
 return np.sqrt(filtered+1e-12)
rx=envelope(x);ry=envelope(y);rz=envelope(z)
L=min(map(len,(rx,ry,rz)))
rx=rx[:L];ry=ry[:L];rz=rz[:L]
source_active=rx>max(.003,float(np.percentile(rx,83))*.20)
converted_present=ry>.001
stable=source_active&converted_present
assert stable.sum()>=350
ratio=20*np.log10((rx+1e-6)/(ry+1e-6))
normal_ratio=float(np.median(ratio[stable]))
loss=ratio-normal_ratio
# An unsupported converted consonant/vowel, not quiet phrase breaks
weak=source_active & (loss>6)
# Distinct narrow fade-ins prevent gating and minimize speaker-color changes
frame_shape=np.clip((loss-6)/12,0,1)*weak
frame_shape=gaussian_filter1d(frame_shape.astype(np.float32),sigma=5.5,mode="nearest")
frame_shape=np.clip(frame_shape,0,1)
# Adapt global carrier level to vocal bed; no per-letter compressor or pitch processing.
positive=source_active&(rz>.001)&(ry>.001)
donor_match_db=float(np.clip(np.median(20*np.log10((ry[positive]+1e-6)/(rz[positive]+1e-6))),-15,15))
zc=z*10**(donor_match_db/20)
q=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
master,ms=sf.read(q["master"],dtype="float32",always_2d=True)
assert ms==sr
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
length=len(master)
def fit(a):
 return np.pad(a,(0,max(0,length-len(a))))[:length]
g=10**(float(q["mix"]["master_gain_db"])/20)
music=master/g-vocal_room(fit(y),sr)
assert np.sqrt(np.mean(((music+vocal_room(fit(y),sr))*g-master)**2))<1e-5
result={"method":"selective gentle 65-90ms source-phase spectral-envelope-recolored phoneme support",
"source_audio_same_generated_singer":True,"primary_voice_same_QA54":True,
"no_new_training":True,"no_live_swap":True,"source_ref_same":True,
"no_user_voice_sample_used_as_vocal_insert":True,
"carrier_origin":"QA67 spectral envelope from QA54 personal conversion, original ACE carrier",
"only_used_if_source_active_and_converted_weak":True,
"original_voice_files_unmodified":True,
"normal_gain_ratio_db":round(normal_ratio,2),
"carrier_level_match_db":round(donor_match_db,2),
"candidates":[]}
from voice_guard42 import check
for max_strength in (.60,.95):
 maskframe=np.clip(frame_shape*max_strength,0,.92)
 times=np.arange(L)*hop
 shape=np.interp(np.arange(N),times,maskframe,left=0,right=0).astype("float32")
 v=(1-shape)*y+shape*zc
 clip=max(float(abs(v).max()),1e-8)
 if clip>.94:v*=.94/clip
 strength_tag="g"+str(int(max_strength*100))
 dry=D/("QA68_GapRescue_"+strength_tag+"_Dry.wav")
 sf.write(dry,v,sr,subtype="FLOAT")
 meter=check(Q/"QA54_CFG090_35s.source.wav",dry,D/("qa68_voice_guard_"+strength_tag+".json"),"ru")
 combined=(music+vocal_room(fit(v),sr))*g
 peak=float(abs(combined).max())
 combined*=min(1,.891/max(peak,1e-8))
 wav=D/("QA68_GapRescue_"+strength_tag+"_35s_Master24.wav")
 mp3=D/("QA68_GapRescue_"+strength_tag+"_35s_320kbps.mp3")
 sf.write(wav,combined,sr,subtype="PCM_24")
 encode=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=90)
 assert encode.returncode==0,encode.stderr[-900:]
 item={"tag":strength_tag,"max_strength":max_strength,
 "frames_reinforced_gt_20pct":int(np.sum(maskframe>.2)),
 "fraction_source_speaker_frame_influence_over_20pct":round(float(np.mean(maskframe>.2)),4),
 "peak_repair_fraction":round(float(np.max(maskframe)),3),
 "total_repair_mass_fraction":round(float(np.mean(maskframe)),4),
 "guard":meter["metrics"],"guard_status":meter["status"],
 "master":str(wav),"dry":str(dry),"mp3":str(mp3),
 "bytes":mp3.stat().st_size,"sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
 "human_speaker_identity_not_proven":True,"human_articulation_not_verified":True}
 result["candidates"].append(item)
 print("QA68_GAP_RESCUE",json.dumps(item,ensure_ascii=True),flush=True)
(D/"qa68_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

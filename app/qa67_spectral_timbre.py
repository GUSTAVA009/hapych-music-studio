"""QA67 low-distortion spectral timbre transfer prototype.
Dry continuous ACE-Step vocal is the acoustic carrier (native phonemes/pitch).
QA54 personal Seed-VC output contributes only slowly varying spectral-envelope
timbre, never its chopped waveform/phase or silence. Not genuine identity VC.
NO production installation. No user-owned recording changes.
"""
from pathlib import Path
import json,hashlib,subprocess,time,sys
import numpy as np,soundfile as sf
from scipy.signal import stft,istft
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA67";D.mkdir(parents=True,exist_ok=True)
Q=R/"Diagnostics"/"QA54"
source=Q/"QA54_CFG090_35s.source.wav"
voice_control=list((R/"Diagnostics"/"QA61"/"original_vocoder").glob("vc_*.wav"))
assert len(voice_control)==1
timbre_donor=voice_control[0]
src,sr=sf.read(source,dtype="float32",always_2d=True)
converted,rs=sf.read(timbre_donor,dtype="float32",always_2d=True)
assert sr==rs==44100
x=src.mean(axis=1);y=converted.mean(axis=1)
n=len(x)
if abs(n-len(y))/sr>.18:raise ValueError("Singing source and donor length mismatch")
y=np.pad(y,(0,max(0,n-len(y))))[:n]
# same source timing; no external speaker or model changes
w=4096;hop=512;noverlap=w-hop
f,t,X=stft(x,fs=sr,nperseg=w,noverlap=noverlap,boundary="zeros",padded=True)
_,_,Y=stft(y,fs=sr,nperseg=w,noverlap=noverlap,boundary="zeros",padded=True)
assert X.shape==Y.shape
X=X.astype("complex64");Y=Y.astype("complex64")
mag_x=abs(X).astype("float32");mag_y=abs(Y).astype("float32")
# Harmonic spacing is uneven across target/source: frequency smooth ~180 Hz
smoothbins=17.0
A=gaussian_filter1d(np.log(np.maximum(mag_x,1e-7)),sigma=smoothbins,axis=0,mode="nearest")
B=gaussian_filter1d(np.log(np.maximum(mag_y,1e-7)),sigma=smoothbins,axis=0,mode="nearest")
diff=np.asarray(B-A,dtype="float32")
del A,B,Y,mag_y,mag_x
# Smooth converted timbre over 0.25s. This excludes momentary per-letter vowel
# resets and noise gating from the converted waveform.
smooth_frames=.23/(hop/sr)
temporal=gaussian_filter1d(diff,sigma=smooth_frames,axis=1,mode="nearest")
frame_rms=np.sqrt(np.mean(np.abs(X)**2,axis=0)).astype("float32")
active=frame_rms>max(float(np.percentile(frame_rms,82))*.2,0.00001)
assert active.sum()>60
# Freeze most of the tone-color correction over whole song; 20% dynamic
# structure remains to follow individual vowel formants.
static=np.median(temporal[:,active],axis=1).astype("float32")
blend=.20
band=(f>=230)&(f<=4200)
freqshape=np.interp(f,[0,110,190,330,4200,5600,8000,sr/2],
                       [0,0,.35,1,1,.25,.04,0]).astype("float32")
correction=(static[:,None]*(1-blend)+temporal*blend).astype("float32")
# Remove overall gain offset, no source or target loudness pumping.
correction-=float(np.median(static[band]))
max_abs_db=4.8
cap=max_abs_db*np.log(10)/20
metadata={"source":str(source),"timbre_donor":str(timbre_donor),
"sample_rate":sr,"fft":w,"hop":hop,"frequency_smoothing_bins":smoothbins,
"temporal_smoothing_seconds":.23,"per_frame_ratio":blend,
"absolute_timbre_eq_ceiling_db":max_abs_db,"source_phase_and_timing_preserved":True,
"seed_vc_phase_and_waveform_NOT_used":True,
"this_is_NOT_full_voice_clone":True,"not_deployed":True,
"phonemes_come_from_original_ACE":True,"owner_must_listen":True,"candidates":[]}
from pathlib import Path
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
q=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
master,master_sr=sf.read(q["master"],dtype="float32",always_2d=True)
prior,prior_sr=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
assert master_sr==prior_sr==sr
length=len(master)
assert abs(length-n)/sr<.18
def fit(a):
 a=a.mean(axis=1)
 return np.pad(a,(0,max(0,length-len(a))))[:length]
gain=10**(float(q["mix"]["master_gain_db"])/20)
backing=master/gain-vocal_room(fit(prior),sr)
assert np.sqrt(np.mean(((backing+vocal_room(fit(prior),sr))*gain-master)**2))<1e-5
for strength in (.60,.95):
 applied=np.clip(correction*freqshape[:,None]*strength,-cap,cap)
 shaped=X*np.exp(applied).astype("float32")
 _,wave=istft(shaped,fs=sr,nperseg=w,noverlap=noverlap,input_onesided=True,boundary=True)
 wave=np.asarray(wave[:n],dtype="float32")
 assert np.isfinite(wave).all()
 # Fixed global level match; no dynamic compressors on Russian consonants.
 ref_rms=float(np.sqrt(np.mean(x*x)+1e-12))
 out_rms=float(np.sqrt(np.mean(wave*wave)+1e-12))
 g=float(np.clip(ref_rms/max(out_rms,1e-8),10**(-1/20),10**(1/20)))
 wave*=g
 peak=float(np.max(np.abs(wave)))
 wave*=min(1.,.89/max(peak,1e-9))
 tag="s"+str(int(strength*100))
 dry=D/("QA67_ContinuousPhonemes_"+tag+"_Dry.wav")
 sf.write(dry,wave,sr,subtype="FLOAT")
 mixed=(backing+vocal_room(np.pad(wave,(0,max(0,length-n)))[:length],sr))*gain
 peak2=float(np.max(np.abs(mixed)))
 mixed*=min(1.,.891/max(peak2,1e-8))
 wav=D/("QA67_ContinuousPhonemes_"+tag+"_Master_24bit.wav")
 mp3=D/("QA67_ContinuousPhonemes_"+tag+"_35s_320kbps.mp3")
 sf.write(wav,mixed,sr,subtype="PCM_24")
 enc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],
 capture_output=True,text=True,timeout=95)
 assert enc.returncode==0,enc.stderr[-1000:]
 item={"strength":strength,"tag":tag,"mono_peak":round(peak,4),
   "global_gain_db":round(20*np.log10(g),2),
   "dry":str(dry),"master":str(wav),"mp3":str(mp3),
   "mp3_bytes":mp3.stat().st_size,"sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
   "deliberately_preserves_original_singer_pronunciation":True,
   "user_voice_identity_not_verified":True}
 metadata["candidates"].append(item)
 print("QA67_CONTINUOUS_SAMPLE",json.dumps(item,ensure_ascii=True),flush=True)
(D/"qa67_report.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA67_READY",len(metadata["candidates"]),flush=True)

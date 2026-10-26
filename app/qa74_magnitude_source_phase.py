"""QA74: full same-lyric QA54 donor spectral-MAGNITUDE transfer with continuous
ACE-Step phase and timing. Contrasts prior QA72 limited-EQ approach.
All modifications isolated to Diagnostics/QA74. No live route change.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,hashlib,subprocess,os,sys,time
from scipy.signal import stft,istft
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA74";D.mkdir(exist_ok=True,parents=True)
Q=R/"Diagnostics"/"QA54"
x,sr=sf.read(Q/"QA54_CFG090_35s.source.wav",dtype="float32",always_2d=True)
donor_path=next((R/"Diagnostics"/"QA61"/"original_vocoder").glob("vc_*.wav"))
y,ys=sf.read(donor_path,dtype="float32",always_2d=True)
assert sr==ys==44100
x=x.mean(axis=1);y=y.mean(axis=1)
n=len(x); assert abs(n-len(y))/sr<.15
y=np.pad(y,(0,max(0,n-len(y))))[:n]
import torch
from scipy.signal import resample_poly
os.environ["HF_HUB_CACHE"]=str(R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1"
os.chdir(R/"Voice Engine"/"seed-vc")
sys.path.insert(0,str(R/"Voice Engine"/"seed-vc"))
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
ck=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
tracker=RMVPE(ck,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
f0=np.asarray(tracker.infer_from_audio(resample_poly(x,160,441).astype(np.float32),thred=0.03),dtype=float)
# Melodic F0 mask only; leave consonants in the native original voice.
FFT=4096;hop=512;OL=FFT-hop
freq,t,X=stft(x,fs=sr,nperseg=FFT,noverlap=OL,boundary="zeros",padded=True)
_,_,Y=stft(y,fs=sr,nperseg=FFT,noverlap=OL,boundary="zeros",padded=True)
X=X.astype(np.complex64)
assert X.shape==Y.shape
rmsx=np.sqrt(np.mean(abs(X)**2,axis=0)+1e-12)
rmsy=np.sqrt(np.mean(abs(Y)**2,axis=0)+1e-12)
voiced=(f0>=70)&(f0<=1100)
voiced_soft=np.interp(t,np.arange(len(voiced))*.01,voiced.astype(float),left=0,right=0)
voiced_soft=gaussian_filter1d(voiced_soft,sigma=.045/(hop/sr))
voiced_soft=np.clip((voiced_soft-.1)/.77,0,1)
src_active=rmsx>max(1e-5,float(np.percentile(rmsx,85))*.18)
gate=gaussian_filter1d(src_active.astype(float),sigma=5)*voiced_soft
gate=np.clip(gate,0,1).astype(np.float32)
# Restore missing QA54 spectra using surrounding neighboring valid timbral shapes,
# NOT missing neural signal. This prevents seams and per-letter dropouts.
level_db=20*np.log10((rmsy+1e-9)/(rmsx+1e-9))
norm=np.median(level_db[src_active & (rmsy>1e-5)])
valid=src_active & (level_db>norm-7.0)
assert valid.sum()>500
Ymag=abs(Y).astype(np.float32)
# Blend between full harmonic magnitudes and a 30-Hz smoothing to suppress tiny noise spikes
Ymag=gaussian_filter1d(Ymag,sigma=2.7,axis=0,mode="nearest")
Xmag=abs(X).astype(np.float32)
Ynorm=np.maximum(np.sqrt(np.mean(Ymag*Ymag,axis=0)),1e-8)
Xnorm=np.maximum(np.sqrt(np.mean(Xmag*Xmag,axis=0)),1e-8)
# Per frame normalized spectrum of QA54 donor; linearly interpolate across poor frames.
# Quantitative pitch remains inherited from X phase.
M=(Ymag/Ynorm[None,:]).astype(np.float32)
idx=np.flatnonzero(valid)
frameidx=np.arange(len(t))
for k in range(M.shape[0]):
 M[k,:]=np.interp(frameidx,idx,M[k,idx]).astype(np.float32)
M=gaussian_filter1d(M,sigma=.045/(hop/sr),axis=1,mode="nearest")
M=np.maximum(M,0)
# Re-normalize to original source vocal's local envelope. This fixes QA54 "dips"
# without creating new gates or pumping; no dry mic voice splicing.
power=np.sqrt(np.mean(M*M,axis=0)+1e-12)
M/=power[None,:]
target=(M*Xnorm[None,:]).astype(np.float32)
# QA54 donor gives singer character; mic sample is its previously approved identity.
# Preserve low drum-free bass and high sibilant release timing from original.
freq_w=np.interp(freq,[0,85,135,210,5600,8000,10500,sr/2],
                 [0,0,.4,1,1,.68,.1,0]).astype(np.float32)
src_phase=np.exp(1j*np.angle(X)).astype(np.complex64)
cfg={"FullMag_35":.35,"FullMag_65":.65,"FullMag_90":.9}
base=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
song,song_sr=sf.read(base["master"],dtype="float32",always_2d=True)
qa54_wav,oldsr=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
assert song_sr==oldsr==sr
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
length=len(song)
def fit(a):
 return np.pad(a,(0,max(0,length-len(a))))[:length]
g=10**(float(base["mix"]["master_gain_db"])/20)
backing=song/g-vocal_room(fit(qa54_wav.mean(axis=1)),sr)
assert np.sqrt(np.mean((((backing+vocal_room(fit(qa54_wav.mean(axis=1)),sr))*g)-song)**2))<1e-5
report={"model":"QA54 owner-associated timbral magnitude onto continuous same-lyrics ACE phase",
"microphone_owner_voice_source":str(R/"Diagnostics"/"QA57"/"reference_selected.wav"),
"same_source_and_master":True,"untouched_owner_mic_data":True,
"no_new_train_or_model_change":True,"not_deployed":True,
"phoneme_timing_and_continuous_phase_kept":True,
"human_quality_or_identity_not_verified":True,
"QA54_invalid_donor_frames_interpolated":int((src_active&~valid).sum()),
"source_pitch_mask":True,"candidate_results":[]}
for name,amount in cfg.items():
 t0=time.monotonic()
 alpha=np.clip((gate*amount)[None,:]*freq_w[:,None],0,.95).astype(np.float32)
 mag=(Xmag*(1-alpha)+target*alpha).astype(np.float32)
 _,signal=istft(mag*src_phase,fs=sr,nperseg=FFT,noverlap=OL,
                input_onesided=True,boundary=True)
 v=signal[:n].astype(np.float32)
 assert np.isfinite(v).all()
 # global gain max +-1dB from original. No local compression.
 old=np.sqrt(np.mean(x*x)+1e-12);new=np.sqrt(np.mean(v*v)+1e-12)
 adjustment=float(np.clip(old/new,10**(-1/20),10**(1/20)))
 v*=adjustment
 vmax=max(float(abs(v).max()),1e-9)
 if vmax>.90:v*=.90/vmax
 dry=D/("QA74_"+name+"_Dry.wav");sf.write(dry,v,sr,subtype="FLOAT")
 mixed=(backing+vocal_room(fit(v),sr))*g
 peak=float(abs(mixed).max())
 mixed*=min(1,.89/max(peak,1e-9))
 wav=D/("QA74_"+name+"_Master24.wav")
 mp3=D/("QA74_"+name+"_35s_320kbps.mp3")
 sf.write(wav,mixed,sr,subtype="PCM_24")
 p=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=90)
 assert p.returncode==0,p.stderr[-700:]
 info={"name":name,"target_mag_strength":amount,
 "avg_blend":round(float(np.mean(alpha)),4),"masked_voiced_fraction":round(float(np.mean(gate>.65)),3),
 "dry":str(dry),"mp3":str(mp3),"master":str(wav),
 "mp3_bytes":mp3.stat().st_size,"sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
 "duration_s":round(n/sr,2),"time_s":round(time.monotonic()-t0,2)}
 report["candidate_results"].append(info)
 print("QA74_CANDIDATE",json.dumps(info,ensure_ascii=True),flush=True)
(D/"qa74_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA74_FINISHED",len(report["candidate_results"]),flush=True)

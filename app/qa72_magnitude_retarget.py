"""QA72 MICROPHONE-ANCHORED DONOR TIMBRE / SOURCE-PHASE RESYNTHESIS
Unlike QA67/70/71 broad EQ, this matches strong time-localized QA54 formant AND
harmonic amplitudes, while original ACE-Step supplies glottal phase, note timing
and voiced continuity. Donor lost-syllable frames are interpolated before transfer.
This is still not an identity-perfect voice-cloning model; human check required.
No original recordings or live serving files are modified.
"""
from pathlib import Path
import numpy as np,soundfile as sf,hashlib,subprocess,json,sys,time
from scipy.signal import stft,istft
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA72";D.mkdir(parents=True,exist_ok=True);Q=R/"Diagnostics"/"QA54"
source=Q/"QA54_CFG090_35s.source.wav"
raw=next((R/"Diagnostics"/"QA61"/"original_vocoder").glob("vc_*.wav"))
mic=R/"Diagnostics"/"QA57"/"reference_selected.wav"
xx,sr=sf.read(source,dtype="float32",always_2d=True)
yy,rs=sf.read(raw,dtype="float32",always_2d=True)
mm,rm=sf.read(mic,dtype="float32",always_2d=True)
assert sr==rs==rm==44100
x=xx.mean(axis=1);y=yy.mean(axis=1);m=mm.mean(axis=1)
n=len(x);y=np.pad(y,(0,max(0,n-len(y))))[:n]
FFT=4096;hop=512;OL=FFT-hop
freq,tt,X=stft(x,fs=sr,nperseg=FFT,noverlap=OL,boundary="zeros",padded=True)
_,_,Y=stft(y,fs=sr,nperseg=FFT,noverlap=OL,boundary="zeros",padded=True)
_,_,M=stft(m,fs=sr,nperseg=FFT,noverlap=OL,boundary="zeros",padded=True)
assert X.shape==Y.shape
X=X.astype(np.complex64)
F,T=X.shape
def env(a):
 return np.sqrt(np.mean(np.abs(a)**2,axis=0)+1e-12).astype(np.float32)
xr=env(X);yr=env(Y);mr=env(M)
active=xr>max(float(np.percentile(xr,85))*.19,1e-5)
micactive=mr>max(float(np.percentile(mr,82))*.2,1e-5)
source_donor=(yr+1e-9)/(xr+1e-9)
ratio_db=20*np.log10(source_donor)
center_db=float(np.median(ratio_db[active & (yr>1e-5)]))
donor_good=active & (ratio_db>center_db-6.5)
assert donor_good.sum()>300
# Fine local harmonic/formant magnitude: smooth only 3 Fourier bins (~30 Hz)
def smoothmag(a):
 return gaussian_filter1d(np.abs(a).astype(np.float32),sigma=3.2,axis=0,mode="nearest")
magx=smoothmag(X);magy=smoothmag(Y);magm=smoothmag(M)
# Fill QA54 amplitude dropouts in spectral domain with nearest valid syllable timbre.
goodidx=np.flatnonzero(donor_good)
frames=np.arange(T)
for i in range(F):
 magy[i,:]=np.interp(frames,goodidx,magy[i,goodidx])
# Smoothed temporal envelope, ~55ms, less than individual vowel duration
magx=gaussian_filter1d(magx,sigma=2.0,axis=1,mode="nearest")
magy=gaussian_filter1d(magy,sigma=.060/(hop/sr),axis=1,mode="nearest")
# Harmonic+formant local ratios, with 5%-of-bin-average stabilization.
eps_x=np.maximum(np.mean(magx,axis=0,keepdims=True)*.04,1e-7)
eps_y=np.maximum(np.mean(magy,axis=0,keepdims=True)*.04,1e-7)
log_ratio=(np.log(magy+eps_y)-np.log(magx+eps_x)).astype(np.float32)
# Remove bulk vocal amplitude difference across target/source
region=(freq>=300)&(freq<=4200)
normal=np.median(log_ratio[region,:],axis=0)
log_ratio-=normal[None,:]
log_ratio=gaussian_filter1d(log_ratio,sigma=1.5,axis=0,mode="nearest")
# Second channel: microphone static spectral signature directly from owner's recording
from_mic=np.median(np.log(magm[:,micactive]+1e-6),axis=1)
from_source=np.median(np.log(magx[:,active]+1e-6),axis=1)
micdiff=from_mic-from_source
micdiff-=float(np.median(micdiff[region]))
micdiff=gaussian_filter1d(micdiff,sigma=8.0,mode="nearest")
# Keep high band under control; preserve original consonant timing and transient phase
freqgain=np.interp(freq,[0,100,150,230,4200,6000,8500,11000,sr/2],
 [0,0,.35,1,1,.85,.45,.10,0]).astype(np.float32)
smooth_gate=gaussian_filter1d(active.astype(np.float32),sigma=5,mode="nearest")
configs={
 "Donor50_Mic30":(.5,.3,16.0),
 "Donor90_Mic35":(.9,.35,22.0),
 "Donor120_Mic35":(1.2,.35,26.0)
}
from sys import path
path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
base=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
master,sa=sf.read(base["master"],dtype="float32",always_2d=True)
old,so=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
assert sr==sa==so
total=len(master)
prev=np.pad(old.mean(axis=1),(0,max(0,total-len(old))))[:total]
g=10**(float(base["mix"]["master_gain_db"])/20)
bed=master/g-vocal_room(prev,sr)
report={"method":"source glottal phase + strong QA54 personal spectral donor + true owner's microphone timbre",
"original_source":str(source),"same_lyrics_qa54_donor":str(raw),
"owner_microphone_reference":str(mic),"own_mic_directly_used":True,
"replacement_audio_inserted":False,"voice_waveform_cut_at_phonemes":False,
"donor_missing_vowels_skipped_and_interpolated":True,
"pitch_and_timing_preserved_by_source_waveform_phase":True,"model_weights_modified":False,
"production_model_not_deployed":True,
"human_identity_quality_not_verified":True,"candidates":[]}
for tag,(dose,identity,capdb) in configs.items():
 start=time.monotonic()
 alpha=(dose*log_ratio+identity*micdiff[:,None])*freqgain[:,None]*smooth_gate[None,:]
 amp=capdb*np.log(10)/20
 alpha=np.clip(alpha,-amp,amp)
 # Apply the donor tone color to the original continuous singer's STFT.
 _,v=istft((X*np.exp(alpha)).astype(np.complex64),fs=sr,nperseg=FFT,noverlap=OL,
     input_onesided=True,boundary=True)
 v=v[:n].astype(np.float32)
 assert np.isfinite(v).all()
 e0=float(np.sqrt(np.mean(x*x)+1e-12));e1=float(np.sqrt(np.mean(v*v)+1e-12))
 gain_global=float(np.clip(e0/e1,10**(-1/20),10**(1/20)))
 v*=gain_global
 peak=float(abs(v).max())
 v*=min(1,.90/max(peak,1e-9))
 dry=D/("QA72_"+tag+"_Dry.wav")
 sf.write(dry,v,sr,subtype="FLOAT")
 vv=np.pad(v,(0,max(0,total-n)))[:total]
 final=(bed+vocal_room(vv,sr))*g
 maxval=float(abs(final).max())
 final*=min(1,.89/max(maxval,1e-9))
 wav=D/("QA72_"+tag+"_Master24.wav");mp3=D/("QA72_"+tag+"_35s_320kbps.mp3")
 sf.write(wav,final,sr,subtype="PCM_24")
 enc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=100)
 assert enc.returncode==0,enc.stderr[-700:]
 meta={"name":tag,"same_lyrics_QA54_donor_strength":dose,
       "actual_owner_mic_strength":identity,"cap_db":capdb,
       "average_eq_db":round(float(np.mean(abs(alpha[region,:]))*20/np.log(10)),2),
       "global_gain_db":round(float(20*np.log10(gain_global)),3),
       "dry":str(dry),"master":str(wav),"mp3":str(mp3),"mp3_bytes":mp3.stat().st_size,
       "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
       "runtime_sec":round(time.monotonic()-start,2),
       "natural_singing_quality_not_proven":True}
 print("QA72_FREQUENCY_RETIMBRE",json.dumps(meta,ensure_ascii=True),flush=True)
 report["candidates"].append(meta)
(D/"qa72_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

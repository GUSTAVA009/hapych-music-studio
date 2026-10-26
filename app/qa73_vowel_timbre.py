"""QA70 OWN-MIC FORMANT/RESONANCE TRANSFER
- Original ACE-Step waveform supplies intact, uninterrupted articulation/F0/phase.
- Direct user microphone (approved 22s QA57 reference) supplies speaker-specific LTAS.
- Matched-lyrics QA54 personal Seed-VC supplies optional formant/resonance dynamics ONLY.
- SOURCE CARRIER NOT REPLACED by Seed-VC waveform; output is not "perfect" voice cloning.
- No external voice, no added singer, no model weights modified, no live deployment.
"""
from pathlib import Path
from scipy.signal import stft,istft
from scipy.ndimage import gaussian_filter1d
import numpy as np,soundfile as sf,hashlib,json,subprocess,time,sys
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA73";D.mkdir(exist_ok=True,parents=True);Q=R/"Diagnostics"/"QA54"
source=Q/"QA54_CFG090_35s.source.wav"
target=R/"Diagnostics"/"QA57"/"reference_selected.wav"
donor=list((R/"Diagnostics"/"QA61"/"original_vocoder").glob("vc_*.wav"))
assert len(donor)==1
donor=donor[0]
for p in (source,target,donor):assert p.is_file()
sx,sr=sf.read(source,dtype="float32",always_2d=True)
tg,rs=sf.read(target,dtype="float32",always_2d=True)
dy,ys=sf.read(donor,dtype="float32",always_2d=True)
assert rs==sr==ys==44100
x=sx.mean(axis=1);mic=tg.mean(axis=1);y=dy.mean(axis=1)
n=len(x);y=np.pad(y,(0,max(0,n-len(y))))[:n]
assert abs(len(x)-len(dy))/sr<.1
fft=4096;hop=512;noverlap=fft-hop
freq,ts,X=stft(x,fs=sr,nperseg=fft,noverlap=noverlap,boundary="zeros",padded=True)
_,_,Y=stft(y,fs=sr,nperseg=fft,noverlap=noverlap,boundary="zeros",padded=True)
_,_,M=stft(mic,fs=sr,nperseg=fft,noverlap=noverlap,boundary="zeros",padded=True)
assert X.shape==Y.shape
X=X.astype(np.complex64);Y=Y.astype(np.complex64)
time_hop=hop/sr
eps=1e-6
def logenv(mat,sigma_bins=13):
 return gaussian_filter1d(np.log(np.abs(mat)+eps).astype(np.float32),sigma=sigma_bins,axis=0,mode="nearest")
logX=logenv(X);logY=logenv(Y);logM=logenv(M)
# Finer harmonic distinction removed; only speech-resonance spectral envelope retained.
def activity(mat):
 rm=np.sqrt(np.mean(np.abs(mat)**2,axis=0))
 return (rm>max(float(np.percentile(rm,82))*.21,1e-5)),rm
active_src,rmsx=activity(X);active_mic,rmsm=activity(M);active_donor,rmsy=activity(Y)
assert active_src.sum()>100 and active_mic.sum()>100 and active_donor.sum()>100
# Long-time average log spectrum of genuinely spoken microphone
own_mu=np.median(logM[:,active_mic],axis=1)
src_mu=np.median(logX[:,active_src],axis=1)
ref_ratio=(own_mu-src_mu).astype(np.float32)
# Timbral difference, remove bulk gain bias; average over formant region only.
region=(freq>=350)&(freq<=4500)
ref_ratio-=np.median(ref_ratio[region])
ref_ratio=gaussian_filter1d(ref_ratio,sigma=7,mode="nearest")
# DONOR difference aligns phonetic cues to the same-source lyrics, with 80ms smoothing.
cont=(logY-logX).astype(np.float32)
valid=active_src&active_donor
# Reject severe donor energy dropout instead of leaking broken syllables into filter.
volume_db=20*np.log10((rmsy+eps)/(rmsx+eps))
norm=np.median(volume_db[valid]);valid&=(volume_db-norm)>-6.5
# Smooth over 0.09s: no rapid per-letter toggles
use=np.flatnonzero(valid)
assert use.size>100
grid=np.arange(cont.shape[1])
for b in range(cont.shape[0]):
 cont[b,:]=np.interp(grid,use,cont[b,use]).astype(np.float32)
cont=gaussian_filter1d(cont,sigma=.09/time_hop,axis=1,mode="nearest")
# Dynamic spectral shape is solely relative, remove broad constant volume multiplier.
donor_offset=np.median(cont[region,:],axis=0)
cont-=donor_offset[None,:]
# Further reject neural high-band shimmer
cont=gaussian_filter1d(cont,sigma=4,axis=0,mode="nearest")
# Formants 280-4600 Hz primary; consonant region 6500+ left unchanged.
wfreq=np.interp(freq,[0,100,180,280,4100,4800,6200,7600,sr/2],
                [0,0,.4,1,1,.8,.35,.05,0]).astype(np.float32)
# Apply gentle activation/fades; protected low-energy intro remains untouched.
env_rms=np.sqrt(np.mean(abs(X)**2,axis=0))
# QA73: direct owner timbre ONLY on stable voiced segments (mostly vowels).
# This leaves consonants and their releases intact, protecting Russian articulation.
from scipy.signal import resample_poly
import os,torch
os.environ["HF_HUB_CACHE"]=str(R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1"
old_cwd=os.getcwd()
os.chdir(str(R/"Voice Engine"/"seed-vc"))
sys.path.insert(0,str(R/"Voice Engine"/"seed-vc"))
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
rmvpe_file=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
rmvpe=RMVPE(rmvpe_file,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
f0=np.asarray(rmvpe.infer_from_audio(resample_poly(x,160,441).astype(np.float32),thred=0.03),dtype=np.float32)
voiced=(f0>70)&(f0<1100)
# F0 at 100Hz; interpolate it to spectral analysis hop (~11.6 ms).
timesteps=np.arange(len(f0))*0.01
sustain=np.interp(ts,timesteps,voiced.astype(np.float32),left=0,right=0)
sustain=gaussian_filter1d(sustain,sigma=.045/time_hop,mode="nearest")
# Prevent the filter from turning on around short pauses.
sustain=np.clip((sustain-.10)/.70,0,1).astype(np.float32)
gate=gaussian_filter1d(active_src.astype(np.float32),sigma=5,mode="nearest")*sustain
gate=np.clip(gate,0,1).astype(np.float32)
os.chdir(old_cwd)
print("QA73_VOWEL_MASK",float(np.mean(gate)),float(np.mean(gate>.6)),flush=True)
# Blend with QA54 and user microphone; hyperparameters chosen a priori, no speaker-metric optimization
configs={
  "Vowel_Mic80_Dyn80":(0.8,0.8,13.0),
  "Vowel_Mic120_Dyn55":(1.2,0.55,14.0),
  "Vowel_Mic100_Dyn15":(1.0,0.15,12.0),
}
base=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
original_master,s_master=sf.read(base["master"],dtype="float32",always_2d=True)
qa54_mixed,s_qa=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
assert sr==s_master==s_qa
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
total=len(original_master)
def fit(a):
 b=a.mean(axis=1)
 return np.pad(b,(0,max(0,total-len(b))))[:total]
gain=10**(float(base["mix"]["master_gain_db"])/20)
bed=original_master/gain-vocal_room(fit(qa54_mixed),sr)
assert np.sqrt(np.mean(((bed+vocal_room(fit(qa54_mixed),sr))*gain-original_master)**2))<1e-5
report={"qa":"QA73","source":"ACE-Step native uninterrupted vocal phase/timing",
 "target_identity_reference_path":str(target),"target_recording_directly_used":True,
 "vowel_only_F0_mask":True,
 "optional_donor":"QA54 same lyrics personal timbre; no donor waveform inserted",
 "frequency_envelope": {"fft":fft,"hop":hop,"freq_gaussian_bins":13,
                         "time_gaussian_s":.09,"target_static_mic_diff_applied":True,
                         "strengths_preselected_not_embedding_hacked":True},
 "models_and_live_pipeline_modified":False,
 "human_identity_verified":False,"human_syllable_continuity_verified":False,
 "full_voice_clone":False,"candidates":[]}
# Source harmonics and phase untouched; no pitch-shift or phoneme segmentation.
for label,(direct_strength,aligned_strength,max_db) in configs.items():
 start=time.monotonic()
 blend=(direct_strength*ref_ratio[:,None]+aligned_strength*cont)
 blend*=wfreq[:,None]*gate[None,:]
 limit=max_db*np.log(10)/20
 blend=np.clip(blend,-limit,limit).astype(np.float32)
 shaped=(X*np.exp(blend)).astype(np.complex64)
 _,audio=istft(shaped,fs=sr,nperseg=fft,noverlap=noverlap,input_onesided=True,boundary=True)
 audio=np.asarray(audio[:n],dtype=np.float32)
 assert np.isfinite(audio).all()
 # global gain matching, no syllable-level processing, 1 dB ceiling
 old=float(np.sqrt(np.mean(x.astype(float)**2)+1e-12))
 new=float(np.sqrt(np.mean(audio.astype(float)**2)+1e-12))
 level=float(np.clip(old/max(new,1e-8),10**(-1/20),10**(1/20)))
 audio*=level
 p=float(abs(audio).max())
 if p>.90:audio*=.90/p
 wavdry=D/("QA73_"+label+"_Dry.wav")
 sf.write(wavdry,audio,sr,subtype="FLOAT")
 combined=(bed+vocal_room(np.pad(audio,(0,max(0,total-n)))[:total],sr))*gain
 p2=float(abs(combined).max())
 combined*=min(1.0,.89/max(p2,1e-9))
 wav=D/("QA73_"+label+"_Master24.wav")
 mp3=D/("QA73_"+label+"_35s_320kbps.mp3")
 sf.write(wav,combined,sr,subtype="PCM_24")
 r=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),"-c:a","libmp3lame",
                    "-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=85)
 assert r.returncode==0,r.stderr
 assert mp3.stat().st_size>1000000
 item={"name":label,"mic_strength":direct_strength,"same_lyrics_donor_strength":aligned_strength,
   "max_correction_db":max_db,"seconds":round(n/sr,2),
   "mean_abs_eq_db":round(float(np.mean(abs(blend[region,:]))*20/np.log(10)),2),
   "peak_eq_db":round(float(np.max(abs(blend))*20/np.log(10)),2),
   "mean_mic_gate":round(float(np.mean(gate)),3),
   "dry":str(wavdry),"master":str(wav),"mp3":str(mp3),
   "mp3_bytes":mp3.stat().st_size,"sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
   "seconds_runtime":round(time.monotonic()-start,2),
   "native_phonemes_preserved_by_source_phase":True,
   "speaker_identity_not_guaranteed":True}
 report["candidates"].append(item)
 print("QA73_CANDIDATE",json.dumps(item,ensure_ascii=True),flush=True)
(D/"qa73_timbre_transfer_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA73_FINISHED",len(report["candidates"]),flush=True)

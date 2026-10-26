"""QA71: microphone-phoneme-conditioned timbre dictionary, same continuous singer phase.
Uses ONLY owner's mic reference plus same-source QA54 timbre color.
F0/word timing/articulation preserved from successful QA67 approach.
No change to production or voice ownership; candidate audition only.
"""
from pathlib import Path
import json,hashlib,subprocess,time,sys
import numpy as np,soundfile as sf
from scipy.signal import stft,istft
from scipy.ndimage import gaussian_filter1d
from scipy.fft import dct
from scipy.spatial import cKDTree
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA71";D.mkdir(parents=True,exist_ok=True);Q=R/"Diagnostics"/"QA54"
x,sr=sf.read(Q/"QA54_CFG090_35s.source.wav",dtype="float32",always_2d=True)
ref,rs=sf.read(R/"Diagnostics"/"QA57"/"reference_selected.wav",dtype="float32",always_2d=True)
don=next((R/"Diagnostics"/"QA61"/"original_vocoder").glob("vc_*.wav"))
qa,qsr=sf.read(don,dtype="float32",always_2d=True)
assert sr==rs==qsr==44100
x=x.mean(axis=1);r=ref.mean(axis=1);y=qa.mean(axis=1)
n=len(x)
y=np.pad(y,(0,max(0,n-len(y))))[:n]
NFFT=4096;H=512;OL=NFFT-H
freq,t,A=stft(x,fs=sr,nperseg=NFFT,noverlap=OL,boundary="zeros",padded=True)
_,_,B=stft(r,fs=sr,nperseg=NFFT,noverlap=OL,boundary="zeros",padded=True)
_,_,C=stft(y,fs=sr,nperseg=NFFT,noverlap=OL,boundary="zeros",padded=True)
assert A.shape==C.shape
A=A.astype("complex64")
def logenv(a):
 return gaussian_filter1d(np.log(np.maximum(abs(a),1e-7)).astype("float32"),
                          sigma=12,axis=0,mode="nearest")
EA=logenv(A);EB=logenv(B);EC=logenv(C)
# timeframes of speech: active voiced not breath-only (spectral lowpass region)
def voiced(a):
 power=np.sqrt(np.mean(abs(a)**2,axis=0))
 main=np.sum(abs(a[(freq>=190)&(freq<=1700),:])**2,axis=0)
 upper=np.sum(abs(a[(freq>4500)&(freq<=10000),:])**2,axis=0)
 m=(power>max(float(np.percentile(power,84))*.20,1e-5))
 return m&(main>upper*.7),power
ma,ra=voiced(A);mb,rb=voiced(B);mc,rc=voiced(C)
assert mb.sum()>100 and ma.sum()>200
# log-spaced channel features approximately corresponding to MFCC speech content
fgrid=np.geomspace(160,5700,72)
indices=np.clip(np.searchsorted(freq,fgrid),1,len(freq)-1)
prev=indices-1
tcoef=((fgrid-freq[prev])/(freq[indices]-freq[prev]+1e-12)).astype(np.float32)
def melgrid_features(env):
 interp=env[prev,:]*(1-tcoef[:,None])+env[indices,:]*tcoef[:,None]
 interp=interp-interp.mean(axis=0,keepdims=True)
 cep=dct(interp,type=2,norm="ortho",axis=0)
 # Skip overall tilt, location-dependent spectral brightness; focus vowel class
 return cep[2:19].T.astype(np.float32)
Fs=melgrid_features(EA);Fm=melgrid_features(EB)
# Independent speaker centering to compare analogous phonetic content.
mean_s=Fs[ma].mean(axis=0);mean_m=Fm[mb].mean(axis=0)
std=(Fs[ma].std(axis=0)+Fm[mb].std(axis=0))*.5
std=np.maximum(std,.12)
src_features=np.clip((Fs-mean_s)/std,-4,4)
mic_features=np.clip((Fm-mean_m)/std,-4,4)
mic_ids=np.flatnonzero(mb)
tree=cKDTree(mic_features[mic_ids])
K=13
dist,ind=tree.query(src_features,k=K,workers=1)
idmic=mic_ids[ind]
# Match the real speaker's vocal-tract envelope per source syllable; using median
# across 13 similar mic frames improves stability and rejects mic noise.
bins=EA.shape[0];T=EA.shape[1]
matching=np.empty((bins,T),dtype=np.float32)
region=(freq>=290)&(freq<=4400)
mic_level=np.median(EB[region,:],axis=0)
src_level=np.median(EA[region,:],axis=0)
# Use intrinsic resonant shape rather than target microphone's raw gain.
EM=EB-mic_level[None,:]
ES=EA-src_level[None,:]
for a in range(0,T,90):
 b=min(T,a+90)
 take=EM[:,idmic[a:b]]  # freq x frames x nearest examples
 matching[:,a:b]=np.median(take,axis=-1).astype("float32")
# Avoid rapidly hopping between unrelated mic phonemes.
matching=gaussian_filter1d(matching,sigma=.075/(H/sr),axis=1,mode="nearest")
mic_global=np.median(EM[:,mb],axis=1)
src_global=np.median(ES[:,ma],axis=1)
static=(mic_global-src_global).astype(np.float32)
static-=float(np.median(static[region]))
static=gaussian_filter1d(static,sigma=7,mode="nearest")
# Dictionary dynamic conversion of source phoneme --> similar real user's phoneme
dictionary=(matching-ES).astype(np.float32)
dictionary-=np.median(dictionary[region,:],axis=0)[None,:]
dictionary=gaussian_filter1d(dictionary,sigma=4,axis=0,mode="nearest")
# Additional same-lyric QA54 speech-specific timbre anchor; no QA54 chopped waveform included.
donor=(EC-EA).astype(np.float32)
valid=ma&mc
diffenergy=20*np.log10((rc+1e-8)/(ra+1e-8))
med=np.median(diffenergy[valid]);valid&=(diffenergy>med-7)
ids=np.flatnonzero(valid)
assert len(ids)>250
grid=np.arange(T)
for bin in range(bins):
 donor[bin,:]=np.interp(grid,ids,donor[bin,ids])
donor=gaussian_filter1d(donor,sigma=.105/(H/sr),axis=1,mode="nearest")
donor-=np.median(donor[region,:],axis=0)[None,:]
donor=gaussian_filter1d(donor,sigma=5,axis=0,mode="nearest")
gainwindow=gaussian_filter1d(ma.astype(np.float32),sigma=5,mode="nearest")
freqweight=np.interp(freq,[0,100,160,260,3700,4600,5800,7100,sr/2],
 [0,0,.5,1,1,.78,.23,.05,0]).astype(np.float32)
cfgs={
 "Dict_55":(.55,.32,.15,11),
 "Dict_100":(1.0,.24,.28,15),
 "Dict_140":(1.4,.25,.38,18)
}
base=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
mix,sm=sf.read(base["master"],dtype="float32",always_2d=True)
old,so=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
assert sm==so==sr
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
total=len(mix);orig=np.pad(old.mean(axis=1),(0,max(0,total-len(old))))[:total]
g=10**(float(base["mix"]["master_gain_db"])/20)
back=mix/g-vocal_room(orig,sr)
report={"qa":71,"method":"phoneme-conditioned nearest-neighbor real microphone formant envelope transplant onto uninterrupted ACE acoustic carrier",
"microphone":str(R/"Diagnostics"/"QA57"/"reference_selected.wav"),
"mic_frames_used":int(mb.sum()),"original_voiced_frames":int(ma.sum()),
"mic_dictionary_size":int(len(mic_ids)),"nearest_mic_frames_per_vowel":K,
"owner_voice_not_yet_verified":True,"native_pitch_and_word_timing_preserved":True,
"phoneme_alignment_matches_by_normalized_cepstrum_not_asr":True,
"qa54_wav_not_spliced":True,"production_untouched":True,
"variant_results":[]}
for tag,(wd,wstatic,wdonor,limit_db) in cfgs.items():
 ratio=wd*dictionary+wstatic*static[:,None]+wdonor*donor
 ratio*=freqweight[:,None]*gainwindow[None,:]
 climit=limit_db*np.log(10)/20
 ratio=np.clip(ratio,-climit,climit)
 if not np.isfinite(ratio).all():raise ValueError("Invalid formant transfer")
 _,v=istft((A*np.exp(ratio)).astype("complex64"),fs=sr,nperseg=NFFT,noverlap=OL,
           input_onesided=True,boundary=True)
 v=np.asarray(v[:n],dtype=np.float32)
 assert np.isfinite(v).all()
 desired=np.sqrt(np.mean(x*x)+1e-12);current=np.sqrt(np.mean(v*v)+1e-12)
 v*=np.clip(desired/current,10**(-1.2/20),10**(1.2/20))
 p=float(abs(v).max())
 v*=min(1,.90/max(p,1e-8))
 dry=D/("QA71_"+tag+"_Dry.wav");sf.write(dry,v,sr,subtype="FLOAT")
 voice=np.pad(v,(0,max(0,total-n)))[:total]
 combined=(back+vocal_room(voice,sr))*g
 peak=float(abs(combined).max());combined*=min(1.,.89/max(peak,1e-8))
 wav=D/("QA71_"+tag+"_Master24.wav")
 mp3=D/("QA71_"+tag+"_35s_320kbps.mp3")
 sf.write(wav,combined,sr,subtype="PCM_24")
 enc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=80)
 assert enc.returncode==0,enc.stderr[-650:]
 stat={"name":tag,"dictionary_strength":wd,"static_mic_strength":wstatic,"QA54_donor_strength":wdonor,
   "max_eq_db":limit_db,"mean_abs_eq_db":round(float(np.mean(abs(ratio[region,:]))*20/np.log(10)),2),
   "dry":str(dry),"wav":str(wav),"mp3":str(mp3),"size":mp3.stat().st_size,
   "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
   "owner_identity_not_confirmed":True,"no_audio_chops":True}
 print("QA71_DONE",json.dumps(stat,ensure_ascii=True),flush=True)
 report["variant_results"].append(stat)
(D/"qa71_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

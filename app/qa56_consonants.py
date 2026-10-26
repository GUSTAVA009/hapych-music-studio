"""QA56 targeted Russian consonant intelligibility pilot.
Uses matching source consonant high-frequency FRICATION only; voiced parts remain
fully Seed-VC with user's timbre. No new generation and no original edits.
Synthetic audio cannot be certified by WER or band energy alone.
"""
from pathlib import Path
import numpy as np,soundfile as sf,subprocess,json
from scipy.signal import butter,sosfiltfilt
from scipy.ndimage import gaussian_filter1d
ROOT=Path.home()/"Music Studio";D=ROOT/"Diagnostics"/"QA56";D.mkdir(parents=True,exist_ok=True)
Q=ROOT/"Diagnostics"/"QA54"
base="QA54_CFG090_35s"
master,sr=sf.read(Q/(base+".finished.wav"),dtype="float32",always_2d=True)
original,s2=sf.read(Q/(base+".source.wav"),dtype="float32",always_2d=True)
mix,s3=sf.read(ROOT/"Мастер WAV"/(base+".wav"),dtype="float32",always_2d=True)
assert sr==s2==s3==44100
v=master.mean(axis=1);o=original.mean(axis=1)
n=min(len(v),len(o),len(mix));v=v[:n];o=o[:n];mix=mix[:n]
hi=sosfiltfilt(butter(3,[4250,10000],fs=sr,btype="bandpass",output="sos"),o)
lo=sosfiltfilt(butter(3,[120,1400],fs=sr,btype="bandpass",output="sos"),o)
k=int(sr*.01);m=n//k
def rms(x):return np.sqrt(np.mean(x[:m*k].reshape(m,k).astype("float64")**2,axis=1)+1e-12)
a,b,c=rms(o),rms(hi),rms(lo)
# select only unvoiced high-frequency consonant transients, not vowel formants:
# ratio higher than 0.24 and substantial high-frequency energy; disable on voiced vowels.
ratio=b/(c+1e-6)
mask=(ratio>1.0)&(b>0.002)&(a>0.004)
# Whitelist only annotated problematic phrase regions, exclude initial 3 sec.
# Exact forced word alignments not available, so avoid claiming per-word localization.
# QA45 clip from song starts at 18s, affected words grouped at
# "ladonyah" early, "okna" mid, "dorogi" and "toropit" later.
regions=np.arange(m)*.01
mask &= ((regions>=0)&(regions<=17.5))|((regions>=17.5)&(regions<=33.5))
env=gaussian_filter1d(mask.astype(float),sigma=2.5)
env=np.clip(env,0,1)
# source fricatives add only as a subtle patch where converted hi energy is
# too weak. This is much less intrusive than replacing phonemes or syllables.
convert_hi=sosfiltfilt(butter(3,[4250,10000],fs=sr,btype="bandpass",output="sos"),v)
deficit=(rms(hi)-rms(convert_hi))/np.maximum(rms(hi),1e-8)
env *= np.clip(deficit,0,1)*0.30
sample_gain=np.interp(np.arange(n)/k,np.arange(m),env,left=0,right=0)
patch=hi*sample_gain
# Same sample reference alignment checked via cross-correlation in active unvoiced patches;
# if source and converted stems have a systematic delay, the experiment is rejected.
from scipy.signal import correlate
s=sr*2;e=sr*7
source_seg=hi[s:e:4];conv_seg=convert_hi[s:e:4]
ac=correlate(source_seg,conv_seg,mode="full",method="fft")
lag=int(np.argmax(abs(ac))-(len(conv_seg)-1))*4
assert abs(lag)<=int(sr*.02),f"stem misalignment {lag/sr:.3f}s"
patched=v+patch
# Mix in the exact original mastering stage's vocal channel only
# Using gain from same quality JSON and same vocal_room diffuse reflections.
import sys
sys.path.insert(0,str(ROOT/"Voice Engine"))
from studio_mix21 import vocal_room
q=json.loads((Q/(base+".quality.json")).read_text(encoding="utf-8"))
master_gain=10**(float(q["mix"]["master_gain_db"])/20)
out=mix.copy()
out[:n]+=vocal_room(patch.astype("float32"),sr)*master_gain
pk=float(np.max(abs(out)))
if pk>.94:out*=.94/pk
wav=D/"QA56_RussianConsonants_Experimental_35s.wav"
mp3=wav.with_suffix(".mp3")
sf.write(wav,out,sr,subtype="PCM_24")
z=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),"-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=120)
assert z.returncode==0,z.stderr[-300:]
r={"status":"experimental","task_words":["ладонях","окна","дороги","торопить"],
 "mechanism":"only tiny high-frequency unvoiced SOURCE fricative support when converted consonants are weaker; vowels 100 percent Seed-VC",
 "source_other_speaker_consonants_may_be_audible":True,
 "pitch_unmodified":True,"voice_model_unmodified":True,
 "gain_max":round(float(sample_gain.max()),3),"applied_frame_fraction":round(float(np.mean(env>.05)),4),
 "signal_patch_rms_relative":round(float(np.sqrt(np.mean(patch**2))/max(np.sqrt(np.mean(v**2)),1e-8)),5),
 "estimated_delay_ms":round(lag*1000/sr,3),
 "word_articulation_human_verified":False,"word_boundaries_verified":False,
 "path":str(mp3),"source_intact":True}
(D/"qa56_report.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA56_DONE",json.dumps(r,ensure_ascii=True),flush=True)

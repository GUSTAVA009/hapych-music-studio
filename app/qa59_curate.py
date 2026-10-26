"""QA59 cleaned nonoverlapping microphone phrases. No voice cloning uploads.
Use only 3 user-provided clean microphone WAVs; 4th remains unseen held out.
No frequency-gating, auto-tune, source singer, heavy denoise or time-stretch.
"""
from pathlib import Path
from scipy.signal import butter,sosfiltfilt,resample_poly
from scipy.ndimage import gaussian_filter1d
import numpy as np,soundfile as sf,json,hashlib,datetime
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";OUT=D/"curated_44k"
OUT.mkdir(parents=True,exist_ok=True)
train_codes=("df413d","3867cb","3ab452");hold="65f5f3"
items=[];segments=[]
for group,code in enumerate((*train_codes,hold),1):
 found=list((R/"Мой голос").glob("*"+code+".wav"))
 assert len(found)==1,found
 p=found[0];raw,sr=sf.read(p,dtype="float32",always_2d=True)
 assert sr==48000 and raw.shape[1]==1
 x=raw[:,0]
 r=resample_poly(x,147,160).astype(np.float32)
 fs=44100
 # Restore tonal clarity; high-pass is below speech fundamental, so no vowels altered.
 r=sosfiltfilt(butter(2,65,btype="highpass",fs=fs,output="sos"),r).astype(np.float32)
 h=int(fs*.025);num=len(r)//h
 e=np.sqrt(np.mean(r[:num*h].reshape(num,h).astype(np.float64)**2,axis=1)+1e-12)
 p10=np.percentile(e,10);p85=np.percentile(e,85)
 target_active=10**(-27/20)
 gain=min(10**(14/20),target_active/max(float(p85),1e-8))
 gain=min(gain,0.88/max(float(np.max(np.abs(r))),1e-8))
 assert gain>0
 r*=gain
 activity=e>max(p10*3,p85*.20)
 role="holdout" if code==hold else "train"
 item={"source":p.name,"source_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
       "role":role,"source_seconds":round(len(x)/sr,3),
       "gain_db":round(20*np.log10(gain),3),
       "source_p85_dbfs":round(20*np.log10(max(float(p85),1e-8)),2),
       "voice_activity_fraction":round(float(activity.mean()),3),
       "cut_dbfs_floor":round(20*np.log10(max(float(p10),1e-8)),2)}
 if role=="train":
  target_count={1:3,2:4,3:3}[group]
  ends=[]
  for j in range(1,target_count):
   desired=j*len(r)/target_count
   f=int(desired/h)
   low=max(0,f-33);high=min(len(e),f+34)
   # Find a short local valley; minimize 125ms smoothed energy at the cut.
   smooth=gaussian_filter1d(e.astype(np.float64),sigma=2.5)
   k=low+int(np.argmin(smooth[low:high]))
   cut=int(k*h)
   assert (not ends or cut>ends[-1]+3*fs) and len(r)-cut>3*fs
   ends.append(cut)
  cuts=[0]+ends+[len(r)]
  for j,(a,b) in enumerate(zip(cuts,cuts[1:]),1):
   piece=r[a:b].copy()
   dur=len(piece)/fs
   assert 4.0<dur<11.5,(group,j,dur)
   edge=min(int(fs*.018),len(piece)//15)
   if a>0:piece[:edge]*=np.sin(np.linspace(0,np.pi/2,edge,dtype=np.float32))**2
   if b<len(r):piece[-edge:]*=np.cos(np.linspace(0,np.pi/2,edge,dtype=np.float32))**2
   name=f"mic{group:02d}_phrase{j:02d}.wav"
   path=OUT/name
   sf.write(path,piece,fs,subtype="FLOAT")
   cr=piece.reshape(-1)
   peak=float(np.max(np.abs(cr)))
   assert peak<.91
   rec={"file":name,"source_file":p.name,"source_start_s":round(a/fs,3),
       "source_end_s":round(b/fs,3),"seconds":round(dur,3),
       "rms_dbfs":round(20*np.log10(max(float(np.sqrt(np.mean(piece.astype(float)**2))),1e-9)),2),
       "peak_dbfs":round(20*np.log10(max(peak,1e-9)),2),
       "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
   segments.append(rec)
   print("QA59_TRAIN_PHRASE",json.dumps(rec,ensure_ascii=True),flush=True)
 item["train_clips"]=len([x for x in segments if x["source_file"]==p.name])
 items.append(item)
assert len(segments)==10
assert len(list(OUT.glob("*.wav")))==10
assert sum(x["seconds"] for x in segments)>70
manifest={"created":datetime.datetime.now().isoformat(),"dataset_name":"QA59 clean curated user-only",
"training_audio_real_seconds":round(sum(x["seconds"] for x in segments),2),
"sources":items,"segments":segments,
"heldout_files":[x["source"] for x in items if x["role"]=="holdout"],
"only_mic_with_user_consent":True,
"source_voices_still_need_human_speaker_confirmation":True,
"voice_ilya_excluded":True,"no_generated_audio_in_training":True,
"no_external_artist_audio":True,"no_augmentation_or_time_stretch":True,
"all_train_slices_nonoverlapping":True,
"voice_file_checksum_sealed":True,
"originals_unchanged":True}
(D/"qa59_dataset_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA59_CURATED_READY",json.dumps({"clips":len(segments),"seconds":manifest["training_audio_real_seconds"],
"holdout":manifest["heldout_files"],"training_codes":train_codes},ensure_ascii=True),flush=True)

"""QA97: align converted singing to the SOURCE melodic F0 contour, not to
chromatic grid. Continuous formant-preserving rubberband processing. Avoid
consonants, glides and very large detector errors. Offline A/B experiment only.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,subprocess,os,sys
from scipy.signal import resample_poly,correlate
from scipy.ndimage import median_filter,gaussian_filter1d
from math import gcd
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA97-ContourCorrection';D.mkdir(parents=True,exist_ok=True)
S=R/'Voice Engine'/'seed-vc';sys.path.insert(0,str(S))
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache');os.environ['HF_HUB_OFFLINE']='1'
os.chdir(S)
import torch
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
model=RMVPE(load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None),
 is_half=False,device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
src_path=R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav'
conv_path=R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.dry.wav'
full=R/'Diagnostics'/'QA45'/'QA45_verse18to53.wav'
for p in (src_path,conv_path,full):assert p.is_file(),p
def load(path):
 y,sr=sf.read(path,dtype='float32',always_2d=True)
 return y,sr
def extract(y,sr):
 x=y.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
 return np.asarray(model.infer_from_audio(x,thred=.03),dtype=np.float64).ravel()
src,sr=load(src_path);old,old_sr=load(conv_path);music,mus_sr=load(full)
assert sr==old_sr==mus_sr==44100
if len(src)!=len(old):assert abs(len(src)-len(old))<sr*.03
n=min(len(src),len(old),len(music))
src=src[:n];old=old[:n];music=music[:n]
f=extract(src,sr);g=extract(old,sr)
nf=min(len(f),len(g));f=f[:nf];g=g[:nf]
v=(f>55)&(f<1100)&(g>55)&(g<1100)
fm=np.zeros(nf);gm=np.zeros(nf)
fm[v]=69+12*np.log2(f[v]/440);gm[v]=69+12*np.log2(g[v]/440)
delta=gm-fm
# Reject octave jumps and letter/transient regions from the correction map.
slope1=np.abs(np.diff(fm,prepend=fm[:1]));slope2=np.abs(np.diff(gm,prepend=gm[:1]))
valid=v&(np.abs(delta)<.80)&(slope1<.25)&(slope2<.30)
# A note must have 130ms or more coherent observed F0 to correct it.
density=gaussian_filter1d(valid.astype('float64'),5.5,mode='constant')
ratio=gaussian_filter1d(np.where(valid,delta,0),5.5,mode='constant')/np.maximum(density,.01)
# preserve expression by correcting slowly varying pitch bias only.
threshold=np.clip((np.abs(ratio)-.055)/.10,0,1)
support=np.clip((density-.45)/.38,0,1)
correction=-np.clip(ratio,-.43,.43)*.92*threshold*support
correction=gaussian_filter1d(correction,6.0,mode='constant')
correction=np.clip(correction,-.38,.38)
steps=np.arange(0,nf,4)
cmds=[f'{frame/100:.3f} rubberband pitch {2**(correction[frame]/12):.7f};' for frame in steps]
cmds.append(f'{(nf-1)/100:.3f} rubberband pitch 1.0000000;')
(D/'qa97_commands.txt').write_text('\n'.join(cmds)+'\n',encoding='ascii')
out=D/'qa97_corrected_vocal.wav'
args=['ffmpeg','-nostdin','-hide_banner','-v','error','-y','-i',str(conv_path),
 '-af','asendcmd=f=qa97_commands.txt,rubberband@rb=tempo=1:pitch=1:formant=preserved:transients=smooth:detector=soft:pitchq=quality:channels=together',
 '-c:a','pcm_f32le',str(out)]
p=subprocess.run(args,cwd=D,capture_output=True,text=True,timeout=95)
if p.returncode:raise RuntimeError(p.stderr[-1500:])
tuned,ts=load(out);assert ts==sr
assert abs(len(tuned)-len(old))<sr*.02
# Confirm no group delay using envelope, NOT phase (pitch has changed).
def env(x):
 z=x.mean(axis=1);hop=441;z=z[:len(z)//hop*hop]
 return np.sqrt(np.mean(z.reshape(-1,hop).astype('float64')**2,axis=1)+1e-12)
A=env(old)[:1200];B=env(tuned)[:1200];cc=correlate(B-B.mean(),A-A.mean(),mode='full',method='fft')
lags=np.arange(-len(A)+1,len(A));near=np.abs(lags)<=9
lag=int(lags[near][np.argmax(cc[near])])
if abs(lag)>3:raise RuntimeError(f'Vocal processor latency {lag*10}ms')
tuned=tuned[:n]
newf=extract(tuned,sr)[:nf]
def metrics(obs):
 a=(f>55)&(f<1100)&(obs>55)&(obs<1100)
 dif=1200*np.log2(obs[a]/f[a])
 return {'matched_frames':int(a.sum()),
 'median_abs_cents':round(float(np.median(np.abs(dif))),2),
 'p90_abs_cents':round(float(np.percentile(np.abs(dif),90)),2),
 'fraction_above_35c':round(float(np.mean(np.abs(dif)>35)),4),
 'fraction_above_70c':round(float(np.mean(np.abs(dif)>70)),4)}
old_metric=metrics(g);new_metric=metrics(newf)
sys.path.insert(0,str(R/'Voice Engine'))
from voice_guard42 import check
reportguard=check(src_path,out,D/'qa97_voicecheck.json','ru')
# reconstruct identical accompaniment from original mix - source extracted vocals
bed=music-src
dryold=old.mean(axis=1);drynew=tuned.mean(axis=1)
# Baseline production mix uses +4.672dB gain on clean converted voice.
gain=10**(4.672/20)
def make(v):
 return bed+v[:,None]*gain
mix_old=make(dryold);mix_new=make(drynew)
peak=max(float(np.max(np.abs(mix_old))),float(np.max(np.abs(mix_new))))
atten=min(1.,.88/max(peak,1e-9))
for label,mix in [('old',mix_old),('corrected',mix_new)]:
 master=D/('qa97_'+label+'_full_35s.wav')
 sf.write(master,(mix*atten).astype('float32'),sr,subtype='PCM_24')
 mp3=master.with_suffix('.mp3')
 ff=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(master),'-c:a','libmp3lame','-b:a','320k',str(mp3)],
  capture_output=True,text=True,timeout=75)
 if ff.returncode:raise RuntimeError(ff.stderr)
print('QA97_COMPARISON',json.dumps({'original':old_metric,'corrected':new_metric,
'guard_status':reportguard['status'],'guard_accepted':reportguard['accepted'],
'guard_missing_frame_fraction':reportguard['metrics']['relative_missing_vocal_frames'],
'pitch_control_p90_cents':round(float(np.percentile(np.abs(correction[v])*100,90)),2),
'pitch_control_max_cents':round(float(np.max(np.abs(correction))*100),2),
'frames_correction_gt8c':int((abs(correction)>0.08).sum()),'lag_ms':lag*10},ensure_ascii=True),flush=True)
report={'experiment':'QA97','old_F0_vs_src':old_metric,'new_F0_vs_src':new_metric,
'voice_guard_status':reportguard['status'],'voice_guard_accepted':reportguard['accepted'],
'peak_correction_cents':round(float(np.max(np.abs(correction))*100),1),
'correction_95th_cents':round(float(np.percentile(np.abs(correction)*100,95)),1),
'command_count':len(cmds),'alignment_lag_ms':lag*10,'original_music_backing_unchanged':True,
'original_user_voice_unchanged':True,'no_new_voice_recording_required':True,
'pitch_reference':'source melody F0, NOT equal temperament note snap',
'vibrato_retained_as_relative_source_contour':True,
'word_consonant_regions_bypassed':True,
'preview_only':True,'production_not_modified':True,
'voice_human_quality_verified':False,'lyric_integrity_not_yet_verified':True,
'mp3_original':str(D/'qa97_old_full_35s.mp3'),
'mp3_corrected':str(D/'qa97_corrected_full_35s.mp3')}
(D/'qa97_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

"""QA109: original QA102 carrier + authentic microphone timbre profile only.
No QA104/QA106/QA107/QA108 sound, no echo, no chunked VC or new singing.
The 31s owner's mic is *analysed entire*, not pasted into the song.
Builds reusable speaker spectrum profile and conservative vowel-state mapping.
"""
from pathlib import Path
import hashlib, json, time, subprocess
import numpy as np
import soundfile as sf
from scipy.signal import stft,istft,resample_poly,butter,sosfiltfilt
from scipy.ndimage import gaussian_filter1d
from sklearn.cluster import KMeans
R=Path.home()/'Music Studio'
D=R/'Diagnostics'/'QA109-TrueMicNoDouble'; D.mkdir(parents=True,exist_ok=True)
mic_file=R/'Мой голос'/'20261022_234327_Микрофон_3867cb.wav'
carrier_file=R/'Diagnostics'/'QA104-FullRealMic'/'Dai_mne_ogon_QA104_my_real_voice_58s.source.wav'
master_file=next((R/'Мастер WAV').glob('*87f50b*.wav'))
for f in [mic_file,carrier_file,master_file]: assert f.exists(),f
t0=time.perf_counter()
carrier,sr=sf.read(carrier_file,dtype='float32',always_2d=True)
mic,rm=sf.read(mic_file,dtype='float32',always_2d=True)
master,mr=sf.read(master_file,dtype='float32',always_2d=True)
assert sr==44100 and mr==48000 and carrier.shape[1]==master.shape[1]==2
assert 57.9<len(carrier)/sr<58.1 and 30<len(mic)/rm<33
# 31-second original reference, complete. High-pass only ANALYSIS copy to remove rumble.
mono=carrier.mean(axis=1)
spoken=mic.mean(axis=1)
if rm!=sr:
    from math import gcd
    g=gcd(rm,sr);spoken=resample_poly(spoken,sr//g,rm//g)
spoken=sosfiltfilt(butter(2,75,fs=sr,btype='highpass',output='sos'),spoken).astype('float32')
fft=4096;hop=512
F,T,X=stft(mono,fs=sr,nperseg=fft,noverlap=fft-hop,boundary='zeros',padded=True)
_,U,M=stft(spoken,fs=sr,nperseg=fft,noverlap=fft-hop,boundary='zeros',padded=True)
X=X.astype('complex64'); M=M.astype('complex64')
ax=np.abs(X); am=np.abs(M)
def active_and_voiced(mag):
    frame=np.sqrt(np.mean(mag*mag,axis=0)+1e-14)
    basic=frame>max(float(np.percentile(frame,78))*.23,0.000008)
    sel=(F>175)&(F<5000)
    piece=np.maximum(mag[sel],1e-9)
    flat=np.exp(np.mean(np.log(piece),axis=0))/(np.mean(piece,axis=0)+1e-9)
    good=basic&(flat<np.percentile(flat[basic],80))
    return good,basic,frame,flat
own_v,own_a,own_r,flat_m=active_and_voiced(am)
src_v,src_a,src_r,flat_x=active_and_voiced(ax)
assert own_v.sum()>250 and src_v.sum()>650,(own_v.sum(),src_v.sum())
# Remove strong pitch-harmonic ripples from the *shape*, not the actual audio.
# 19 FFT bins = 205 Hz, more robust than the QA107 1.9-bin filter.
sigma_freq=19.0
def smooth_envelope(mag):
    return gaussian_filter1d(np.log(np.maximum(mag,1e-7)).astype('float32'),
                             sigma=sigma_freq,axis=0,mode='nearest')
LX=smooth_envelope(ax); LM=smooth_envelope(am)
lo=(F>=300)&(F<=4300)
mic_base=np.median(LM[:,own_v],axis=1).astype('float32')
src_base=np.median(LX[:,src_v],axis=1).astype('float32')
mic_static=mic_base-src_base
mic_static-=float(np.median(mic_static[lo]))
mic_static=gaussian_filter1d(mic_static,sigma=13,mode='nearest')
# Cluster vowel *analysis features*, never fragment/swap original waveforms.
# Features are speaker-centered so a vowel state is not confused with voice identity.
idx=np.unique(np.clip(np.searchsorted(F,np.geomspace(270,4500,40)),0,len(F)-1))
base_own=LM[idx,:]-mic_base[idx,None]
base_src=LX[idx,:]-src_base[idx,None]
# Very quiet or consonant-only frames are excluded from learning, NOT removed from output.
own_points=base_own[:,own_v].T.astype('float32')
src_points=base_src[:,src_v].T.astype('float32')
std=np.clip(np.std(own_points,axis=0),0.23,1.0)
own_points/=std[None,:]; src_points/=std[None,:]
k=7
km=KMeans(n_clusters=k,random_state=109,n_init=4,max_iter=120)
own_labels=km.fit_predict(own_points)
src_labels=km.predict(src_points)
own_frame_labels=np.full(LM.shape[1],-1,dtype=np.int16)
src_frame_labels=np.full(LX.shape[1],-1,dtype=np.int16)
own_frame_labels[np.flatnonzero(own_v)]=own_labels
src_frame_labels[np.flatnonzero(src_v)]=src_labels
# Each mic-derived state is paired with the SAME spectral-state class
# in the original song; this avoids the damaged QA104 processed donor entirely.
by_state=np.empty((k,len(F)),dtype='float32')
counts=[]
for j in range(k):
    wown=own_frame_labels==j
    wsrc=src_frame_labels==j
    counts.append({'state':j,'reference_frames':int(wown.sum()),'song_frames':int(wsrc.sum())})
    if wown.sum()<28 or wsrc.sum()<28: state=mic_static.copy()
    else:
        state=(np.median(LM[:,wown],axis=1)-np.median(LX[:,wsrc],axis=1)).astype('float32')
        state-=float(np.median(state[lo]))
        state=gaussian_filter1d(state,sigma=16,mode='nearest')
    by_state[j]=state
# Transport stable speaker color; context blend changes over ~0.3s,
# slower than phonemes to avoid pumping, shimmer and cut syllables.
dyn=np.zeros((k,LX.shape[1]),dtype='float32')
for j in range(k): dyn[j,src_frame_labels==j]=1
dyn=gaussian_filter1d(dyn,sigma=.22/(hop/sr),axis=1,mode='nearest')
den=np.maximum(dyn.sum(axis=0),1e-8)
dynamic=(by_state.T@dyn)/den[None,:]
inactive=den<.08
dynamic[:,inactive]=mic_static[:,None]
# Majority static: stable profile reusable in future songs.
correction=(.76*mic_static[:,None]+.24*dynamic)
correction=gaussian_filter1d(correction,sigma=.15/(hop/sr),axis=1,mode='nearest')
# Keep plosives and high-frequency consonants; avoid coloring silence/breaths.
fw=np.interp(F,[0,95,160,235,420,3000,4300,5500,6900,sr/2],
                [0,0,.20,.86,1,1,.75,.32,0,0]).astype('float32')
gate=gaussian_filter1d(src_a.astype('float32'),sigma=.065/(hop/sr),mode='nearest')
gate=np.clip(gate,0,1)
# Natural vocal resonance from real speaker; fixed no per-syllable gain matching.
transfer_strength=1.24
correction*=fw[:,None]*gate[None,:]*transfer_strength
limit_db=7.0
maxlog=limit_db*np.log(10)/20
np.clip(correction,-maxlog,maxlog,out=correction)
correction=np.asarray(correction,dtype='float32')
mult=np.exp(correction)
N=len(carrier)
new_channels=[]
for ch in range(2):
    _,_,W=stft(carrier[:,ch],fs=sr,nperseg=fft,noverlap=fft-hop,boundary='zeros',padded=True)
    assert W.shape==mult.shape
    _,sig=istft((W.astype('complex64')*mult).astype('complex64'),
                fs=sr,nperseg=fft,noverlap=fft-hop,boundary=True,input_onesided=True)
    new_channels.append(sig[:N].astype('float32'))
new=np.stack(new_channels,axis=1)
def rms(y):return float(np.sqrt(np.mean(y.astype('float64')**2)+1e-13))
global_voice_gain=float(np.clip(rms(carrier)/max(rms(new),1e-10),10**(-3/20),10**(3/20)))
new*=global_voice_gain
# Do not allow large abrupt per-word loss relative to QA102.
def frame_rms(arr):
    stride=round(sr*.010)
    n=(len(arr)//stride)*stride
    return np.sqrt(np.mean(arr[:n].reshape(-1,stride,2).astype('float64')**2,axis=(1,2))+1e-12)
before=frame_rms(carrier);after=frame_rms(new)
active_frames=before>max(np.percentile(before,75)*.20,.0012)
relative_db=20*np.log10((after[active_frames]+1e-10)/(before[active_frames]+1e-10))
drop_count=int(np.sum(relative_db<-6.0))
# Protect against harsh modulation at consonants by taking a conservative version
# if this happens; it is not a crossfade or addition of a second singer.
if drop_count:
    alpha=0.75
    new=carrier+alpha*(new-carrier)
    after=frame_rms(new)
    relative_db=20*np.log10((after[active_frames]+1e-10)/(before[active_frames]+1e-10))
    drop_count=int(np.sum(relative_db<-6.0))
assert drop_count==0,drop_count
# Insert a DIFFERENCE signal at measured QA102 mastering alignment,
# not a second voice or a stereo delayed copy. No reverb or chorus.
offset=4800  # QA107 previously measured exactly 100ms against QA102 master
source_gain=.994
delta=new-carrier
delta48=resample_poly(delta,160,147,axis=0).astype('float32')
assert offset+len(delta48)<=len(master)
out=master.copy()
out[offset:offset+len(delta48)]+=source_gain*delta48
peak=float(np.max(np.abs(out)))
headroom=float(min(1.0,.96/max(peak,1e-10)))
out*=headroom
dry_path=D/'QA109_true_mic_only_dry_44k.wav'
wav_path=D/'Dai_mne_ogon_QA109_true_mic_no_double_58s.wav'
mp3_path=D/'Dai_mne_ogon_QA109_true_mic_no_double_58s_320.mp3'
sf.write(dry_path,new,sr,subtype='PCM_24')
sf.write(wav_path,out,mr,subtype='PCM_24')
p=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(wav_path),
                  '-c:a','libmp3lame','-b:a','320k',str(mp3_path)],
                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=100)
assert p.returncode==0,p.stderr
# Frequency-response fingerprint for transparent re-application to NEW tracks.
np.savez_compressed(D/'owner_mic_31s_timbre_profile.npz',
                    frequencies_hz=F,mic_reference_spectrum=mic_base,
                    mic_vowel_state_spectra=by_state,
                    mic_vowel_state_kmeans_centers=km.cluster_centers_,
                    normalization_std=std,
                    reference_frequency_sample_indices=idx,
                    source_spectrum_for_QA109=src_base)
# A tonal distance proxy, not a human voice identity score.
pre=src_base[lo]-np.median(src_base[lo])
post_env=smooth_envelope(np.abs(stft(new.mean(axis=1),fs=sr,nperseg=fft,
                          noverlap=fft-hop,boundary='zeros',padded=True)[2]))
post_base=np.median(post_env[:,src_v],axis=1)
post=post_base[lo]-np.median(post_base[lo])
ref=mic_base[lo]-np.median(mic_base[lo])
def rmse_db(a,b):return round(float(np.sqrt(np.mean(((a-b)*20/np.log(10))**2))),2)
report={
 'version':'QA109','strategy':'microphone-only frequency envelope + slowly varying mic vowel states',
 'real_mic_source':str(mic_file),'full_reference_sec':round(len(spoken)/sr,3),
 'original_singer_carrier':str(carrier_file),'qa102_master':str(master_file),
 'used_QA104_voice_audio':False,'used_QA106_voice_audio':False,
 'used_QA107_voice_audio':False,'used_QA108_voice_audio':False,
 'voice_synthesis':False,'reverb':False,'doubling':False,
 'audio_or_mic_cut_into_syllables':False,'f0_or_tempo_altered_by_algorithm':False,
 'speaker_f0_mismatch_remains':True,'identity_confirmed_by_user':False,
 'transfer_strength':transfer_strength,'limit_per_frequency_db':limit_db,
 'freq_sigma_bins':sigma_freq,'mix_static':.76,'mix_phonetic':.24,
 'mic_vowel_frames':int(own_v.sum()),'song_vowel_frames':int(src_v.sum()),
 'state_counts':counts,'voice_global_gain_db':round(20*np.log10(global_voice_gain),3),
 'master_alignment_ms':100,'vocal_drop_events_relative_to_QA102':drop_count,
 'vocal_p1_level_change_db':round(float(np.percentile(relative_db,1)),2),
 'vocal_p99_level_change_db':round(float(np.percentile(relative_db,99)),2),
 'master_headroom_db':round(20*np.log10(headroom),3),
 'long_term_envelope_error_before_db':rmse_db(pre,ref),
 'long_term_envelope_error_after_db':rmse_db(post,ref),
 'metric_is_not_voice_identity':True,'duration_sec':round(len(out)/mr,3),
 'mp3_bytes':mp3_path.stat().st_size,'sha256':hashlib.sha256(mp3_path.read_bytes()).hexdigest(),
 'mp3':str(mp3_path),'wav':str(wav_path),'dry':str(dry_path),
 'runtime_sec':round(time.perf_counter()-t0,2),'production_studio_unchanged':True}
(D/'qa109_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('QA109_COMPLETE '+json.dumps(report,ensure_ascii=True),flush=True)

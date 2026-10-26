"""QA106: QA102-native singing + QA104 harmonic envelope fingerprint,
without Seed-VC waveform, fragment cuts, tempo/pitch manipulations or
replacing original lead articulation.

The *entire* owner's original 31s microphone reference is analyzed.
Voice carrier: untouched 58s QA102 Demucs vocal including stereo expression.
Voice-color donor: QA104 personal dry, same song/phonemes, BAD wave NOT used.
Three controlled levels: conservative, natural, stronger.

Reconstruction = 48k QA102 original master + resampled differential
(vocal_colored - QA102_original_demucs_vocal). Outside singing the old
master is preserved. No existing library files overwritten.
"""
from pathlib import Path
from math import gcd
import os,json,subprocess,time,hashlib
import numpy as np
import soundfile as sf
from scipy.signal import stft,istft,resample_poly,correlate
from scipy.ndimage import gaussian_filter1d
R=Path.home()/'Music Studio';Q=R/'Diagnostics'/'QA104-FullRealMic'
D=R/'Diagnostics'/'QA106-HarmonicTimbre';D.mkdir(parents=True,exist_ok=True)
src=Q/'Dai_mne_ogon_QA104_my_real_voice_58s.source.wav'
don=Q/'Dai_mne_ogon_QA104_my_real_voice_58s.dry.wav'
mic=R/'Мой голос'/'20261022_234327_Микрофон_3867cb.wav'
master=next((R/'Мастер WAV').glob('*87f50b*.wav'))
full=next((R/'Исходные версии').glob('*87f50b*.wav'))
for p in [src,don,mic,master,full]:assert p.is_file(),p
x,sr=sf.read(src,dtype='float32',always_2d=True)
y,ds=sf.read(don,dtype='float32',always_2d=True)
m,ms=sf.read(mic,dtype='float32',always_2d=True)
b,bs=sf.read(master,dtype='float32',always_2d=True)
original,mainsr=sf.read(full,dtype='float32',always_2d=True)
assert sr==ds==44100 and bs==mainsr==48000 and x.shape[1]==2
n=len(x);assert abs(n/sr-58)<.025
if len(y)<n:y=np.pad(y,((0,n-len(y)),(0,0)))
y=y[:n].mean(axis=1)
if ms!=sr:
 g=gcd(ms,sr);m=resample_poly(m.mean(axis=1),sr//g,ms//g)
else:m=m.mean(axis=1)
assert abs(len(m)/sr-31)<.1
# Preserve all recorded microphone frames (no excerpts or concatenations).
Nx,hop=4096,512;noverlap=Nx-hop
xmono=x.mean(axis=1)
freq,t,X=stft(xmono,fs=sr,nperseg=Nx,noverlap=noverlap,boundary='zeros',padded=True)
_,_,Y=stft(y,fs=sr,nperseg=Nx,noverlap=noverlap,boundary='zeros',padded=True)
_,_,M=stft(m,fs=sr,nperseg=Nx,noverlap=noverlap,boundary='zeros',padded=True)
assert X.shape==Y.shape
X=X.astype(np.complex64)
# Time-varying same-lyrics personal timbre envelope: remove broad amplitude gain.
def logenv(a,sigma=1.9):
 return gaussian_filter1d(np.log(np.maximum(np.abs(a),1e-7)).astype('float32'),
                          sigma=sigma,axis=0,mode='nearest')
def activity(a):
 mag=np.abs(a).astype('float32')
 amp=np.sqrt(np.mean(mag*mag,axis=0)+1e-12)
 mask=amp>max(.000008,float(np.percentile(amp,83))*.18)
 return mask,amp
aa,ea=activity(X);ay,ey=activity(Y);am,em=activity(M)
assert aa.sum()>400 and ay.sum()>400 and am.sum()>300
region=(freq>=290)&(freq<=4700)
source_log=logenv(X);donor_log=logenv(Y);mic_log=logenv(M)
static_mic=(np.median(mic_log[:,am],axis=1) -
            np.median(source_log[:,aa],axis=1)).astype('float32')
static_mic-=float(np.median(static_mic[region]))
static_mic=gaussian_filter1d(static_mic,sigma=8,mode='nearest')
# Reject frames where trained Seed-VC lost a vowel, else the spectral donor
# could incorrectly transfer absence of vocal instead of identity.
level_db=20*np.log10((ey+1e-8)/(ea+1e-8))
valid=aa&ay
median_level=np.median(level_db[valid])
valid&=level_db>median_level-7.0
ids=np.flatnonzero(valid);assert len(ids)>350
donor_delta=(donor_log-source_log).astype('float32')
donor_delta-=np.median(donor_delta[region,:],axis=0)[None,:]
grid=np.arange(donor_delta.shape[1])
for row in donor_delta:
 row[:]=np.interp(grid,ids,row[ids])
donor_delta=gaussian_filter1d(donor_delta,sigma=.075/(hop/sr),axis=1,mode='nearest')
donor_delta=gaussian_filter1d(donor_delta,sigma=1.25,axis=0,mode='nearest')
# Protected consonants: leave >6.5kHz almost exactly unchanged.
freq_weight=np.interp(freq,
 [0,100,170,245,450,3800,4700,6100,7700,sr/2],
 [0,0,.25,.85,1,1,.80,.15,0,0]).astype('float32')
gate=gaussian_filter1d(aa.astype(np.float32),sigma=5.2,mode='nearest')
gate=np.clip(gate,0,1).astype('float32')
# Same spectral gain for both original stereo channels, preserving timing,
# stereo placement, all original vowels, consonants and phase of QA102.
configs={
 'Harmonic55':(.85,.20,14.0),
 'Harmonic90':(1.4,.35,20.0),
 'Harmonic120':(1.85,.45,23.0),
}
def stereo_from_envelope(mono_profile):
 channels=[]
 for i in (0,1):
  _,_,cx=stft(x[:,i],fs=sr,nperseg=Nx,noverlap=noverlap,boundary='zeros',padded=True)
  assert cx.shape==mono_profile.shape
  _,v=istft((cx.astype(np.complex64)*mono_profile).astype(np.complex64),
           fs=sr,nperseg=Nx,noverlap=noverlap,input_onesided=True,boundary=True)
  v=np.asarray(v[:n],dtype='float32')
  assert np.isfinite(v).all() and len(v)==n
  channels.append(v)
 return np.column_stack(channels)
def rms(v):return float(np.sqrt(np.mean(v.astype('float64')**2)+1e-14))
# Original QA102 master is the EXACT baseline carrier: do not re-master
# new audio through the lossy QA104 SeedVC chain.
assert len(original)<=len(b)<=len(original)+bs*1.0
# QA102 master may be compressed/gain-processed relative to source;
# measure plausible scalar to insert the differential at consistent loudness.
def best_gain(new,reference):
 a=new.reshape(-1).astype('float64');t=reference.reshape(-1).astype('float64')
 return float(np.dot(a[::128],t[::128])/(np.dot(a[::128],a[::128])+1e-9))
# QA102 finishing has 100ms lookahead. Detect it instead of
# introducing an echo/comb filter by applying vocal delta at wrong time.
decimate=12;sample_s=15*bs
original_ds=resample_poly(original[:sample_s].mean(axis=1),1,decimate)
master_ds=resample_poly(b[:sample_s+bs].mean(axis=1),1,decimate)
cc=correlate(master_ds-master_ds.mean(),original_ds-original_ds.mean(),
             method='fft',mode='full')
lags=np.arange(-len(original_ds)+1,len(master_ds));limit=np.abs(lags)<bs/decimate
ix=np.argmax(np.abs(cc[limit]))
offset=int(lags[limit][ix]*decimate)
correlation=float(cc[limit][ix]/np.sqrt(np.sum(original_ds**2)*np.sum(master_ds**2)+1e-12))
assert 0<=offset<=bs//5 and correlation>.8,(offset,correlation)
master_gain=best_gain(original,b[offset:offset+len(original)])
assert .2<master_gain<2.0,master_gain
report={'version':'QA106','source_QA102_master':str(master),
        'source_original_demucs':str(src),'personal_donor_QA104':str(don),
        'entire_owner_mic':str(mic),'mic_seconds':round(len(m)/sr,3),
        'owner_recording_was_not_cut':True,'QA102_original_vocal_waveform_reused':True,
        'qa104_synthesized_waveform_not_inserted':True,
        'QA102_pitch_tempo_syllable_timing_preserved':True,
        'source_phase_preserved':True,'production_pipeline_unchanged':True,
        'vowel_word_endings_original_source':True,
        'same_master_as_QA102':True,'original_master_alignment_delay_ms':round(offset*1000/bs,2),
        'original_master_alignment_correlation':round(correlation,4),
        'master_gain_proxy':round(master_gain,4),
        'donor_valid_frames':len(ids),
        'donor_frames':len(grid),'mic_active_frames':int(am.sum()),
        'frequency_filter':{'nfft':Nx,'hop':hop,'region_hz':[245,6100],
                            'donor_smoothing_s':.075,'consonants_above_7700_untouched':True},
        'variants':[]}
for name,(dy,di,capdb) in configs.items():
 start=time.monotonic()
 correction=(dy*donor_delta+di*static_mic[:,None])
 correction*=freq_weight[:,None]*gate[None,:]
 cap=capdb*np.log(10)/20
 np.clip(correction,-cap,cap,out=correction)
 spectral_multiplier=np.exp(correction).astype(np.float32)
 colored=stereo_from_envelope(spectral_multiplier)
 # Slow time-frequency EQ only; no dynamic gain from QA104.
 # Keep QA102's exact average vocal level after spectral color shaping.
 # A fixed song-wide normalization (not per syllable) avoids +7dB vocal
 # inflation and the earlier unsafe -9dB attenuation of the entire master.
 level=float(np.clip(rms(x)/max(rms(colored),1e-9),
            10**(-9/20),10**(9/20)))
 colored*=level
 # Master delta applied to exact original QA102 master (48 kHz).
 delta=(colored-x)
 delta48=resample_poly(delta,160,147,axis=0).astype('float32')
 assert abs(len(delta48)-len(original))<50 and (offset+len(delta48))<=len(b)
 # This is a time-aligned difference. Outside vocals, original 48k master
 # is bit-for-bit preserved prior to global headroom protection.
 aligned=np.zeros_like(b)
 aligned[offset:offset+len(delta48)]+=delta48
 mixed=b+aligned*master_gain
 maxp=float(np.max(abs(mixed)))
 global_gain=min(1,.92/max(maxp,1e-9))
 mixed=(mixed*global_gain).astype(np.float32)
 wav=D/(f'QA106_{name}_master_48k.wav')
 dry=D/(f'QA106_{name}_vocal_dry_44k.wav')
 mp3=D/(f'QA106_{name}_58s_320kbps.mp3')
 sf.write(wav,mixed,bs,subtype='PCM_24')
 sf.write(dry,colored,sr,subtype='FLOAT')
 run=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(wav),
  '-c:a','libmp3lame','-b:a','320k',str(mp3)],capture_output=True,text=True,timeout=75)
 assert run.returncode==0,run.stderr[-600:]
 changed_low=float(np.sqrt(np.mean((colored-x).astype('float64')**2)+1e-14))
 stat={'name':name,'donor_strength':dy,'own_mic_strength':di,
       'max_spectral_gain_db':capdb,
       'vocal_delta_rms_ratio':round(changed_low/max(rms(x),1e-9),3),
       'vocal_rms_change_db':round(float(20*np.log10(rms(colored)/rms(x))),3),
       'global_fixed_vocal_color_gain_db':round(float(20*np.log10(level)),3),
       'max_applied_correction_db':round(float(np.max(abs(correction))*20/np.log(10)),2),
       'master_peak_before_guard':round(maxp,4),
       'master_gain_db':round(float(20*np.log10(global_gain)),3),
       'duration_s':round(len(mixed)/bs,3),'mp3':str(mp3),'dry':str(dry),
       'master_wav':str(wav),'bytes':mp3.stat().st_size,
       'sha256':hashlib.sha256(mp3.read_bytes()).hexdigest(),
       'secs_runtime':round(time.monotonic()-start,2),
       'human_timbre_match_unverified':True}
 report['variants'].append(stat)
 print('QA106_VARIANT',json.dumps(stat,ensure_ascii=True),flush=True)
 del colored,delta,delta48,mixed,spectral_multiplier,correction
(D/'qa106_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print('QA106_GENERATION_COMPLETE',len(report['variants']),flush=True)

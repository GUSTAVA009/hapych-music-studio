"""QA105 objective verification, run on preserved QA102 carrier and
three spectral donor strengths. CAMPPlus is a proxy, not voice identity
proof. RMVPE estimates pitch; STFT source phase is never replaced.
"""
from pathlib import Path
from math import gcd
import os,sys,json,torch,torchaudio
import soundfile as sf,numpy as np
from scipy.signal import resample_poly, butter, sosfiltfilt
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA106-HarmonicTimbre'
S=R/'Voice Engine'/'seed-vc'
os.chdir(S);sys.path.insert(0,str(S));sys.path.insert(0,str(R/'Voice Engine'))
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache')
os.environ['HF_HUB_OFFLINE']='1'
from hf_utils import load_custom_model_from_hf
from modules.campplus.DTDNN import CAMPPlus
from modules.rmvpe import RMVPE
from voice_guard42 import check
import torchaudio.compliance.kaldi as kaldi
torch.set_num_threads(4)
device='cuda' if torch.cuda.is_available() else 'cpu'
ckpt=load_custom_model_from_hf('funasr/campplus','campplus_cn_common.bin',config_filename=None)
speaker=CAMPPlus(feat_dim=80,embedding_size=192)
speaker.load_state_dict(torch.load(ckpt,map_location='cpu',weights_only=True))
speaker.eval().to(device)
f0ckpt=load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None)
rmvpe=RMVPE(f0ckpt,is_half=False,device=torch.device(device))
source=R/'Diagnostics'/'QA104-FullRealMic'/'Dai_mne_ogon_QA104_my_real_voice_58s.source.wav'
donor=R/'Diagnostics'/'QA104-FullRealMic'/'Dai_mne_ogon_QA104_my_real_voice_58s.dry.wav'
mic=R/'Мой голос'/'20261022_234327_Микрофон_3867cb.wav'
files={'QA102_original':source,'QA104_personal':donor,
       'QA106_Harmonic55':D/'QA106_Harmonic55_vocal_dry_44k.wav',
       'QA106_Harmonic90':D/'QA106_Harmonic90_vocal_dry_44k.wav',
       'QA106_Harmonic120':D/'QA106_Harmonic120_vocal_dry_44k.wav'}
def loadmono(f):
 y,sr=sf.read(f,dtype='float32',always_2d=True)
 assert len(y)/sr>=24
 return y.mean(axis=1),sr
def shrink(x,sr):
 if sr!=16000:
  g=gcd(sr,16000)
  return resample_poly(x,16000//g,sr//g).astype('float32')
 return x
def embed(f):
 x,sr=loadmono(f)
 x=shrink(x[:int(25*sr)],sr)
 v=torch.from_numpy(x.copy())
 feat=kaldi.fbank(v[None],num_mel_bins=80,dither=0,sample_frequency=16000)
 feat-=feat.mean(dim=0,keepdim=True)
 with torch.no_grad():return speaker(feat.unsqueeze(0).to(device)).reshape(-1)
v_owner=embed(mic)
embeddings={}
for name,p in files.items():
 embeddings[name]=embed(p)
 print('SPEAKER_EMBED',name,flush=True)
def cosine(a,b):
 return round(float(torch.nn.functional.cosine_similarity(a[None],b[None]).item()),4)
def pitch(f):
 x,sr=loadmono(f)
 y=shrink(x[:int(30*sr)],sr)
 return np.asarray(rmvpe.infer_from_audio(y,thred=.03),dtype='float64').ravel()
ref_pitch=pitch(source)
print('QA105_REF_PITCH_READY',len(ref_pitch),flush=True)
report={'reference_mic_full_sec':round(len(loadmono(mic)[0])/loadmono(mic)[1],2),
        'method':'QA102 carrier with QA104 and owner mic timbre envelopes',
        'pitch_source':'QA102 existing original song, NOT model-generated QA104',
        'speaker_similarity_proxy_only':True,'human_speaker_identity_verified':False,
        'variants':{}}
for label,f in files.items():
 obs=pitch(f)
 n=min(len(obs),len(ref_pitch))
 o=obs[:n];s=ref_pitch[:n];voiced=(o>55)&(o<1100)&(s>55)&(s<1100)
 assert voiced.sum()>400
 cents=1200*np.log2(o[voiced]/s[voiced])
 y,sr=loadmono(f);x,refsr=loadmono(source)
 assert sr==refsr and abs(len(y)-len(x))<=len(x)*.003
 N=min(len(y),len(x));x=x[:N];y=y[:N]
 def blockrms(z):
  hop=int(sr*.01);usable=len(z)//hop*hop
  return np.sqrt(np.mean(z[:usable].reshape(-1,hop).astype('float64')**2,axis=1)+1e-11)
 e0=blockrms(x);e1=blockrms(y)
 active=e0>max(.002,np.percentile(e0,75)*.2)
 rd=20*np.log10((e1[active]+1e-10)/(e0[active]+1e-10))
 jumps=int(np.sum(rd < np.median(rd)-10))
 # Confirm voiceless /s/ region not modified at >7.7kHz except small STFT leak
 high=sosfiltfilt(butter(3,7600,btype='highpass',fs=sr,output='sos'),x)
 highb=sosfiltfilt(butter(3,7600,btype='highpass',fs=sr,output='sos'),y)
 corr=float(np.corrcoef(high[::40],highb[::40])[0,1])
 check_data=check(source,f,D/(label+'.voicecheck.json'),'ru') if label.startswith('QA106') else None
 stat={'owner_embedding_cosine':cosine(v_owner,embeddings[label]),
       'source_embedding_cosine':cosine(embeddings['QA102_original'],embeddings[label]),
       'p50_abs_f0_error_cents':round(float(np.percentile(abs(cents),50)),2),
       'p90_abs_f0_error_cents':round(float(np.percentile(abs(cents),90)),2),
       'above35c_fraction':round(float(np.mean(abs(cents)>35)),4),
       'above70c_fraction':round(float(np.mean(abs(cents)>70)),4),
       'matching_voiced_frames':int(voiced.sum()),
       'extra_10db_energy_dips':jumps,
       'ultrahigh_consonant_band_correlation':round(corr,5),
       'voice_guard_accepted':check_data.get('accepted') if check_data else None,
       'voice_guard_status':check_data.get('status') if check_data else None,
       'voice_guard_missing_fraction':check_data.get('metrics',{}).get('relative_missing_vocal_frames') if check_data else None,
       'owner_identity_not_verified':True}
 report['variants'][label]=stat
 print('QA106_METRIC',label,json.dumps(stat,ensure_ascii=True),flush=True)
(D/'qa106_metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

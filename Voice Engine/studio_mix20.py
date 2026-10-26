"""Match the source vocal level with one constant gain; do not impose a universal vocal/backing target."""
import numpy as np
import soundfile as sf
from studio_mix16 import read_audio,declick,deess,db,EPS

def power_frames(x,hop):
    a=np.asarray(x,dtype=np.float64)
    if a.ndim==1:a=a[:,None]
    missing=(-len(a))%hop
    if missing:a=np.pad(a,((0,missing),(0,0)))
    return np.sqrt(np.mean(a.reshape(-1,hop,a.shape[1])**2,axis=(1,2))+EPS)

def finish(vocal,backing,source_vocal,processed_path,mixed_path,sr=44100):
    v=read_audio(vocal,sr).mean(axis=1);b=read_audio(backing,sr);reference=read_audio(source_vocal,sr)
    n=len(b);drift=(len(v)-n)/sr
    if abs(drift)>.35:raise ValueError('Converted vocal length mismatch')
    v=np.pad(v,(0,max(0,n-len(v))))[:n]
    reference=np.pad(reference,((0,max(0,n-len(reference))),(0,0)))[:n]
    v=v-np.mean(v);v,clicks=declick(v);v,sibilants=deess(v,sr)
    hop=sr//100;rv=power_frames(v,hop);rr=power_frames(reference,hop);rb=power_frames(b,hop)
    active=(rr>max(10**(-48/20),float(np.percentile(rr,85))*.15))&(rv>10**(-55/20))
    if active.sum()<10:raise ValueError('Too little measurable voice')
    gain_db=float(np.clip(np.median(db(rr[active])-db(rv[active])),-24,18))
    v*=10**(gain_db/20)
    if b.shape[1]==1:b=np.repeat(b,2,axis=1)
    if b.shape[1]>2:b=b[:,:2]
    mixed=b+v[:,None];peak=float(np.max(np.abs(mixed)));attenuation=min(1,.94/max(peak,EPS))
    sf.write(str(processed_path),v,sr,subtype='FLOAT');sf.write(str(mixed_path),mixed*attenuation,sr,subtype='PCM_24')
    return {'method':'source_level_constant_gain_v20','gain_db':round(gain_db,3),'dynamic_gain_used':False,
            'source_vocal_backing_db':round(float(np.median(db(rr[active])-db(rb[active]))),3),
            'result_vocal_backing_db':round(float(np.median(db(power_frames(v,hop)[active])-db(rb[active]))),3),
            'stereo_energy_measurement':'mean_square_per_channel_not_mono_sum','duration_seconds':n/sr,
            'gate_used':False,'pitch_modified_by_mixer':False,'source_vocal_blended':False,
            'deesser':sibilants,'clicks_repaired':clicks,'master_gain_db':round(float(db(attenuation)),3),
            'acoustic_quality_verified':False}

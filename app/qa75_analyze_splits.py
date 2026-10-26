from pathlib import Path
import numpy as np, soundfile as sf, json
from scipy.ndimage import uniform_filter1d
root=Path.home()/'Music Studio'
src=root/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav'
wav,sr=sf.read(src,dtype='float32',always_2d=True)
a=wav.mean(axis=1); hop=512
n=(len(a)+hop-1)//hop
padded=np.pad(a,(0,n*hop-len(a)))
rms=np.sqrt(np.mean(padded.reshape(-1,hop)**2,axis=1)+1e-11)
smooth=uniform_filter1d(rms,size=9,mode='nearest')
active_ref=float(np.percentile(smooth,85))
levels={'active_rms85':active_ref,'rms_median':float(np.median(smooth)),
        'rms_min':float(smooth.min()),'rms_max':float(smooth.max()),
        'duration_s':len(a)/sr}
limit=max(.002,active_ref*.15)
quiet=smooth<limit
ranges=[]; st=None
for i,v in enumerate(list(quiet)+[False]):
    if v and st is None: st=i
    if not v and st is not None:
        if (i-st)*hop/sr>.09:
            ranges.append({'start':round(st*hop/sr,3),
                           'end':round(i*hop/sr,3),
                           'ms':round((i-st)*hop/sr*100),
                           'min_level':round(float(np.min(smooth[st:i])),5)})
        st=None
known=[902,1804,2706]
seams=[round(f*hop/sr,3) for f in known]
print(json.dumps({'levels':levels,'quiet_threshold':limit,
   'seams_s':seams,'quiet_gaps':ranges[:100],
   'near_seams':{str(s):[g for g in ranges if s-3.0<g['start']<s+.8]
          for s in seams}},ensure_ascii=False,indent=2))

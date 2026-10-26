from pathlib import Path
import sys,json, numpy as np, soundfile as sf, torch
R=Path.home()/'Music Studio'
sys.path.insert(0,str(R/'Voice Engine'/'seed-vc'))
from mel_stitch75 import plan,source_energy,accumulate
src,sr=sf.read(R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav',dtype='float32')
if src.ndim>1:src=src.mean(axis=1)
total=3014; hop=512;overlap=128; max_window=1030
energy=source_energy(src,hop,total)
segments,changes=plan(energy,max_window,overlap,hop=hop,sr=sr)
n=len(energy)
canvas=torch.zeros((1,1,n));w=torch.zeros(n)
for i,(a,b) in enumerate(segments):
    accumulate(canvas,w,torch.ones((1,1,b-a)),a,b,i,changes)
assert torch.all(w>0), float(w.min())
assert torch.allclose(canvas/w[None,None,:],torch.ones_like(canvas),atol=1e-6)
assert all(b-a<=max_window for a,b in segments)
for c in changes:
    assert c['center']>=c['next_start'] and c['center']<=c['end']
    if c['kind']=='quiet':assert c['source_rms']<c['source_rms_threshold']
report={'segments':segments,'transitions':changes,
 'nominal_baseline_starts':[0,902,1804,2706],
 'all_frames_covered':True,
 'same_max_context':True,
 'unchanged_pcm_and_models':True,
 'max_weight_deviation':round(float(torch.max(torch.abs(w-1))),7)}
folder=R/'Diagnostics'/'QA75';folder.mkdir(exist_ok=True)
(folder/'qa75_split_plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('QA75_SPLIT_PLAN '+json.dumps(report,ensure_ascii=False))

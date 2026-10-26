"""QA35: compare original ACE-Step audio and final QA34, find sound events.
The output is measurable audio diagnostics only; never claim automatic detection
of exact spoken words or sound quality from objective waveform features.
"""
from pathlib import Path
import json, numpy as np,soundfile as sf
from scipy.signal import resample_poly, stft
root=Path.home()/"Music Studio"
originals=list((root/"Исходные версии").glob("*QA34*.wav"))
masters=list((root/"Мастер WAV").glob("*QA34*.wav"))
assert len(originals)==len(masters)==1,(len(originals),len(masters))
orig,sr=sf.read(str(originals[0]),dtype="float32",always_2d=True)
final,fr=sf.read(str(masters[0]),dtype="float32",always_2d=True)
print("FILES",str(originals[0]),str(masters[0]))
print("DUR",len(orig)/sr,len(final)/fr,"RATE",sr,fr)
if fr!=sr:
  from math import gcd
  g=gcd(fr,sr);final=resample_poly(final,sr//g,fr//g,axis=0)
off=int(.1*sr)
aligned=final[off:off+len(orig)]
n=min(len(aligned),len(orig))
aligned=aligned[:n];orig=orig[:n]
# Estimate stereo similarity and differences between ACE generation and final master.
def db(x):
 return float(20*np.log10(max(1e-10,np.sqrt(np.mean(x.astype("float64")**2)))))
results=[]
hop=int(.5*sr)
for start in range(0,n-hop,hop):
  o=orig[start:start+hop];m=aligned[start:start+hop]
  peak_o=float(np.max(np.abs(o)));peak_m=float(np.max(np.abs(m)))
  ratio=float(np.sum(o.astype("float64")*m.astype("float64"))/(np.sum(o.astype("float64")**2)+1e-10))
  err=m-o*ratio
  results.append({"time_s":round(start/sr,2),"source_db":round(db(o),2),
                  "final_db":round(db(m),2),"diff_db":round(db(err),2),
                  "best_gain_db":round(20*np.log10(max(1e-8,abs(ratio))),2),
                  "peak_source":round(peak_o,3),"peak_final":round(peak_m,3)})
print("FIRST_16_SECONDS")
for x in results[:32]:print(x)
print("LARGEST_SOURCES_TO_MASTER_DIFF")
for x in sorted(results,key=lambda x:x["diff_db"],reverse=True)[:12]:print(x)
# Tempo map approximates beats; report precise grid labels but no false assertion of beat alignment.
bpm=92.;beat=60/bpm;bar=beat*4.
print("92_BPM_BEAT_SECONDS",beat,"BAR_SECONDS",bar)
print("SUGGESTED_BAR_STARTS",[round(i*bar,2) for i in range(0,6)])
# RMS during first twelve seconds for planning soundbed shape
r=Path(root/"Diagnostics"/"QA35");r.mkdir(parents=True,exist_ok=True)
(r/"qa34_compare.json").write_text(json.dumps({"format":"source_v_final",
  "original":str(originals[0]),"master":str(masters[0]),"source_duration_s":len(orig)/sr,
  "master_duration_s":len(final)/fr,"grid":{"bpm":92,"bar_s":bar},
  "half_second":results},ensure_ascii=False,indent=2),encoding="utf-8")
print("SAVED",r/"qa34_compare.json")

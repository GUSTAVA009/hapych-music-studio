"""Pitch range measurement from the selected reference, with no gender inference."""
import argparse,json,sys,warnings
from pathlib import Path
import numpy as np,librosa
warnings.filterwarnings('ignore')
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'seed-vc'))
from modules.rmvpe import RMVPE
p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--output',required=True);a=p.parse_args()
weights=list((HERE/'seed-vc'/'checkpoints').rglob('rmvpe.pt'))
if not weights:raise FileNotFoundError('Cached pitch extractor not found')
y,sr=librosa.load(a.reference,sr=16000,mono=True,duration=45)
if len(y)<32000:raise ValueError('Reference shorter than two seconds')
f0=RMVPE(str(weights[0]),is_half=False,device='cpu').infer_from_audio(y,thred=.03)
f=np.asarray(f0);voiced=f[np.isfinite(f)&(f>=55)&(f<=700)]
report={'reliable':len(voiced)>=50,'voiced_frames':len(voiced),'seconds_analyzed':len(y)/sr}
if report['reliable']:
 low,median,high=np.percentile(voiced,[15,50,85])
 report.update(p15_hz=round(float(low),2),median_hz=round(float(median),2),p85_hz=round(float(high),2))
 report['hint']='Невысокая вокальная тесситура, связное пение.' if median<145 else 'Средняя вокальная тесситура, связное пение.' if median<210 else 'Высокая вокальная тесситура, связное пение.'
Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))

"""QA100 synthetic intonation regression. No audio files modified."""
from pathlib import Path
import sys,numpy as np
sys.path.insert(0,str(Path.home()/'Music Studio'/'Voice Engine'/'seed-vc'))
from voice_intonation100 import measure
a=np.full(600,200.0)
cases=[('precise',a,200*np.power(2,15/1200)*np.ones_like(a),'not_flagged'),
       ('detuned',a,200*np.power(2,55/1200)*np.ones_like(a),'review'),
       ('unvoiced',np.zeros_like(a),np.zeros_like(a),'not_proven'),
       ('matching',a,a,'not_flagged')]
for name,src,out,expected in cases:
 report=measure(src,out)
 assert report['status']==expected,(name,report)
 assert report['report_only'] and not report['note_corrected']
 print('QA100_TEST_PASS',name,report['status'],report.get('p90_abs_pitch_error_cents'),flush=True)

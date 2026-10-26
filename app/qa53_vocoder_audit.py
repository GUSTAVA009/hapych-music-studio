"""QA53 exact sample-level BigVGAN chunk-boundary inspection.
This checks *two different* boundaries: vocoder 512 mel frame cut
and mel synthesis chunks. No audio modified.
"""
from pathlib import Path
import json,numpy as np,soundfile as sf
R=Path.home()/"Music Studio";Q=R/"Diagnostics"/"QA52";D=R/"Diagnostics"/"QA53";D.mkdir(exist_ok=True)
test=Q/"QA52_18sPrompt_35s.dry.wav"
orig=Q/"QA52_18sPrompt_35s.source.wav"
voc=Q/"QA52_18sPrompt_35s.finished.wav"
quality=json.loads((Q/"QA52_18sPrompt_35s.quality.json").read_text(encoding="utf-8"))
parts={"source_ace":orig,"seedvc_dry":test,"seedvc_finished":voc}
audio={}
for label,path in parts.items():
 y,sr=sf.read(path,dtype="float32",always_2d=True)
 audio[label]=y.mean(axis=1)
 assert sr==44100,(sr,label)
 assert len(audio[label])>30*sr
hop=512;body=512
seams=[i*hop*body for i in range(1,7) if i*hop*body<len(audio["seedvc_dry"])]
print("CHECKED_VOCODER_BOUNDARIES_SECONDS",[round(x/sr,4) for x in seams],flush=True)
report={}
for key,y in audio.items():
 dx=np.abs(np.diff(y))
 rms=(np.sqrt(np.convolve(y[::80].astype(float)**2,np.ones(55)/55,mode="same")+1e-12))
 diag=[]
 for idx in seams:
  window=int(sr*.06);before=y[idx-window:idx];after=y[idx:idx+window]
  left_rms=float(np.sqrt(np.mean(before**2)+1e-10));right_rms=float(np.sqrt(np.mean(after**2)+1e-10))
  median_step=float(np.median(np.abs(np.diff(y[max(0,idx-window):idx+window]))))
  jump=float(abs(y[idx]-y[idx-1]))
  # Normalized to median absolute *ordinary* per-sample steps in a 120ms local band.
  jump_ratio=jump/max(median_step,1e-7)
  local_amp_ratio=abs(20*np.log10(max(left_rms,1e-6)/max(right_rms,1e-6)))
  diag.append({"t":round(idx/sr,3),"sample_jump":round(jump,5),
              "jump_vs_local_median_derivative":round(jump_ratio,1),
              "rms_level_change_db_60ms":round(local_amp_ratio,2)})
 # compare with random non-boundary changes
 ctl=[]
 for idx in [int((i+.5)*sr) for i in range(34) if int((i+.5)*sr)<len(y)]:
  win=int(sr*.06)
  ctl.append(float(abs(y[idx]-y[idx-1])/max(np.median(np.abs(np.diff(y[idx-win:idx+win]))),1e-7)))
 print("CUT_AUDIT",key,json.dumps(diag,ensure_ascii=True),"CONTROL_P95",round(float(np.percentile(ctl,95)),2),flush=True)
 report[key]={"seams":diag,"control_p95_derivative":round(float(np.percentile(ctl,95)),2)}
(D/"qa53_vocoder_boundary_audit.json").write_text(json.dumps({"hop":hop,"body_frames":body,"vocoder_boundary_audit":report,
 "qa52_mel_boundaries_frames":quality["stitching"]["chunk_starts_frames"],
 "note":"Large single sample jumps are one potential source of clicks; not all neural syllable ruptures are waveform clicks."},ensure_ascii=False,indent=2),encoding="utf-8")

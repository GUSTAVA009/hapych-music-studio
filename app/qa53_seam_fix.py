"""QA53 strictly-local waveform continuity test on existing QA52 dry voice.
Repair only sample discontinuity at deterministic vocoder cut positions.
A 4 ms interpolated sine-eased bridge cannot fix vowel accent or lost phonemes.
"""
from pathlib import Path
import json,numpy as np,soundfile as sf,subprocess,sys
R=Path.home()/"Music Studio";Q=R/"Diagnostics"/"QA52";D=R/"Diagnostics"/"QA53"
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
src=Q/"QA52_18sPrompt_35s.dry.wav"
quality=json.loads((Q/"QA52_18sPrompt_35s.quality.json").read_text(encoding="utf-8"))
dry,sr=sf.read(src,dtype="float32",always_2d=True)
mono=dry.mean(axis=1).copy();n=len(mono)
positions=[i*512*512 for i in range(1,8) if i*512*512<n]
edits=[]
for ix in positions:
 win=int(sr*.06)
 before=mono[ix-win:ix];after=mono[ix:ix+win]
 med=float(np.median(abs(np.diff(mono[ix-win:ix+win]))))
 jump=float(abs(mono[ix]-mono[ix-1]))
 loud=float(abs(20*np.log10(max(np.sqrt(np.mean(before**2)),1e-7)/max(np.sqrt(np.mean(after**2)),1e-7))))
 # Only rejoin if transient is excessive; avoids altering correct consonant attacks.
 if not(jump/max(med,1e-7)>3 and loud>5):continue
 width=max(16,int(sr*.003))
 a=ix-width;b=ix+width
 base=mono[a:b].copy()
 # Correct only the differential offset, fade it out by 3ms on either side.
 discontinuity=float(mono[ix]-mono[ix-1])
 offsets=np.zeros(len(base),dtype=np.float32)
 # subtract half of discontinuity on the right and add half on left, smoothly to zero
 t=np.linspace(0,1,width,dtype=np.float32)
 offsets[:width]=.5*discontinuity*np.sin(.5*np.pi*t)**2
 offsets[width:]=-.5*discontinuity*np.cos(.5*np.pi*t)**2
 mono[a:b]+=offsets
 edits.append({"t_s":round(ix/sr,3),"before_jump":round(jump,5),"after_jump":round(float(abs(mono[ix]-mono[ix-1])),5),
               "window_ms":round(2*width/sr*1000,2),"left_right_rms_diff_db":round(loud,2)})
# only 6 ms edited per affected boundary
stem=D/"QA53_VocoderSeams_CleanVocal.wav"
sf.write(stem,mono,sr,subtype="FLOAT")
# Reconstruct original QA52 mix from backing extracted by subtracting *the same* studio vocal room.
master,sr2=sf.read(quality["master"],dtype="float32",always_2d=True)
assert sr2==sr
finished,sr3=sf.read(Q/"QA52_18sPrompt_35s.finished.wav",dtype="float32",always_2d=True)
assert sr3==sr
old=finished.mean(axis=1)
gain=10**(float(quality["mix"]["gain_db"])/20)
mgain=10**(float(quality["mix"]["master_gain_db"])/20)
# Reuse studio processing for the seam delta on the postdeess, postgain stem;
# don't alter source backing or reapply mastering twice.
delta=(mono-dry.mean(axis=1))*gain
mix=master.copy()
change=vocal_room(delta.astype("float32"),sr)*mgain
m=min(len(mix),len(change))
mix[:m]+=change[:m]
peak=float(np.max(abs(mix)))
if peak>.98:mix*=.98/peak
wav=D/"QA53_VocoderSeamAB_35s.wav";mp3=wav.with_suffix(".mp3")
sf.write(wav,mix,sr,subtype="PCM_24")
ret=subprocess.run(["ffmpeg","-nostdin","-y","-v","error","-i",str(wav),"-c:a","libmp3lame","-b:a","320k",str(mp3)],
 capture_output=True,text=True,timeout=90)
if ret.returncode:raise RuntimeError(ret.stderr[-600:])
report={"based_on":"QA52 existing synthesis","seam_edits":edits,
 "full_voice_model_unmodified":True,"song_unchanged":True,
 "phoneme_content_reconstructed":False,"pronunciation_corrected":False,
 "true_vocal_dropout_repaired":False,"audio":str(mp3),"duration_seconds":len(mono)/sr,
 "method":"only short correction at objectively abrupt BigVGAN waveform cut boundaries"}
(D/"qa53_seam_result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA53_SEAM_AB",json.dumps(report,ensure_ascii=True),flush=True)

"""QA95 read-only chord-vocal consonance audit, no pitch editing.

Compute instrument harmonic chroma and compare stable singer pitch classes.
Dissonance is a *screen*, not proof of incorrect note: jazz suspensions, passing
tones and blue notes may be intentional. Output timestamps for manual review.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,librosa,time
from scipy.signal import resample_poly
from scipy.ndimage import median_filter
from math import gcd
ROOT=Path.home()/'Music Studio'
d=ROOT/'Diagnostics'/'QA95-Harmony';d.mkdir(parents=True,exist_ok=True)
stem=ROOT/'Diagnostics'/'QA86-SFTBenchmark'/'sft_stems'/'htdemucs'/'sft_35s'
pitch=np.load(ROOT/'Diagnostics'/'QA93-Intonation'/'SFT_source_f0_100hz.npy')
bed,sr=sf.read(stem/'no_vocals.wav',dtype='float32',always_2d=True)
mono=bed.mean(axis=1)
if sr!=22050:g=gcd(sr,22050);mono=resample_poly(mono,22050//g,sr//g)
t=time.monotonic()
# Time-local chroma of chordal backing, low-register included.
chroma=librosa.feature.chroma_cqt(y=mono,sr=22050,hop_length=512,n_chroma=12,
                                  fmin=librosa.note_to_hz('C1'),n_octaves=7,
                                  threshold=0.0)
chroma=np.maximum(chroma,0)
chroma=chroma/np.maximum(np.sum(chroma,axis=0,keepdims=True),1e-8)
keys=list(librosa.midi_to_note(np.arange(60,72),octave=False,unicode=False))
glob=np.mean(chroma,axis=1)
major=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
minor=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
grades=[]
for mode,profile in [('major',major),('minor',minor)]:
 for tonic in range(12):
  p=np.roll(profile,tonic)
  score=float(np.corrcoef(glob,p)[0,1])
  grades.append((score,keys[tonic],mode))
grades=sorted(grades,reverse=True)
# Identify individual held-note runs and score chroma in the note's interval.
valid=(pitch>58)&(pitch<1100)
m=np.full(len(pitch),np.nan);m[valid]=69+12*np.log2(pitch[valid]/440)
qnote=np.where(valid,np.rint(median_filter(np.where(valid,m,0),size=9)),-999).astype(int)
notes=[];i=0
while i<len(qnote):
 k=qnote[i];j=i+1
 while j<len(qnote) and qnote[j]==k:j+=1
 if k>0 and j-i>=13:
  inner=m[i+min(3,(j-i)//5):j-min(3,(j-i)//5)]
  inner=inner[np.isfinite(inner)]
  if len(inner)>=8:
   med=float(np.median(inner))
   cents=(med-k)*100
   if abs(cents)<=35:
    left=max(0,int((i/100+0.03)*22050/512))
    right=min(chroma.shape[1],int((j/100-0.03)*22050/512)+1)
    if right>left:
     local=np.mean(chroma[:,left:right],axis=1)
     own=float(local[k%12]);rank=float(np.mean(local>own))
     total_beat=float(local.sum())
     notes.append({'at':round(i/100,2),'end':round(j/100,2),
                   'note':keys[k%12],'midi':int(k),'cents_from_equal_note':round(cents,1),
                   'instrument_support':round(own,4),
                   'stronger_instrument_pitch_classes':int(np.sum(local>own)),
                   'out_of_chord_candidate':bool(rank>=.75 and (j-i)>=24),
                   'duration_s':round((j-i)/100,2)})
 i=j
flagged=[x for x in notes if x['out_of_chord_candidate']]
# Note: huge chord consonance scores may still be distorted by drums/harmonics.
report={'top_global_keys':[{'key':f'{tonic} {mode}','confidence_correlation':round(sc,3)} for sc,tonic,mode in grades[:6]],
'backing_global_pitchclass':{name:round(float(w),3) for name,w in zip(keys,glob)},
'stable_vocal_notes_analyzed':len(notes),'potential_nonchord_long_notes':len(flagged),
'long_note_mismatches':flagged[:30],'note_segments':notes,'audio_seconds':len(bed)/sr,
'key_inference_is_uncertain':True,
'passing_tones_are_legitimate':True,
'original_music_voice_never_changed':True,
'analysis_seconds':round(time.monotonic()-t,2)}
(d/'qa95_harmony_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('QA95_HARMONY',json.dumps({k:v for k,v in report.items() if k not in ('note_segments','backing_global_pitchclass')},ensure_ascii=True),flush=True)

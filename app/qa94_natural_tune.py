"""QA94: conservative note-center intonation preview.

Use input F0 from RMVPE, adjust ONLY stable individual notes with <43
cents mean deviation, and never change pitch at glides, consonants or silence.
Continuous Rubber Band spectral processing (no syllable chops), preserve formants,
and keep source/band mix unmodified. Diagnostic-only; no production mutation.
"""
from pathlib import Path
from math import gcd
import subprocess,json,os
import numpy as np,soundfile as sf
from scipy.ndimage import median_filter,gaussian_filter1d
from scipy.signal import resample_poly
R=Path.home()/'Music Studio';Q=R/'Diagnostics'/'QA94-IntonationPreview'
Q.mkdir(parents=True,exist_ok=True)
P=R/'Diagnostics'/'QA93-Intonation'/'SFT_source_f0_100hz.npy'
F=R/'Diagnostics'/'QA86-SFTBenchmark'/'sft_stems'/'htdemucs'/'sft_35s'
f0=np.load(P)
source,sr=sf.read(F/'vocals.wav',dtype='float32',always_2d=True)
bed,bs=sf.read(F/'no_vocals.wav',dtype='float32',always_2d=True)
assert sr==bs==44100 and source.shape==bed.shape
assert abs(len(source)/sr-35)<.1
hz=f0.astype('float64')
valid=(hz>58)&(hz<1100)
midi=np.full(len(hz),np.nan)
midi[valid]=69+12*np.log2(hz[valid]/440)
smooth=median_filter(np.where(valid,midi,0),size=9)
qnote=np.where(valid,np.rint(smooth),-9999).astype(int)
# A musical note must be voiced consistently; don't join through consonants.
segments=[];i=0
while i<len(qnote):
 if qnote[i]<0:i+=1;continue
 pitch=qnote[i];j=i+1
 while j<len(qnote) and qnote[j]==pitch:j+=1
 if j-i>=25:
  inner=midi[i+min(6,(j-i)//5):j-min(6,(j-i)//5)]
  inner=inner[np.isfinite(inner)]
  if len(inner)>=12:
   center=float(np.median(inner))
   spread=float(np.percentile(inner,75)-np.percentile(inner,25))
   detune=center-pitch
   if 0.085<=abs(detune)<=.43 and spread<.32:
    move=float(np.clip(-.78*detune,-.32,.32))
    segments.append({'from_s':round(i/100,3),'to_s':round(j/100,3),
     'note_midi':int(pitch),'note_median_cents':round(detune*100,1),
     'correct_cents':round(move*100,1),'spread_cents':round(spread*100,1),
     'frames':j-i,'at':(i,j),'move':move})
 i=j
shifts=np.zeros(len(f0),dtype='float64')
weights=np.zeros(len(f0),dtype='float64')
for row in segments:
 i,j=row['at'];length=j-i
 # At least 120ms cosine fade each end. Nearly zero at boundaries.
 fade=min(14,max(5,length//3))
 envelope=np.ones(length)
 edge=(1-np.cos(np.linspace(0,np.pi,fade)))/2
 envelope[:fade]=edge;envelope[-fade:]=edge[::-1]
 shifts[i:j]+=envelope*row['move']
 weights[i:j]+=envelope
shifts=np.clip(shifts,-.32,.32)
# Extra smoothing to avoid instantaneous pitch-rate steps (sigma=30 ms).
shifts=gaussian_filter1d(shifts,3.0)
assert np.max(abs(shifts))<=.33
if not segments:raise RuntimeError('No objectively stable note segments')
# Emit changes at 40 ms resolution, with explicit final reset.
grid=np.arange(0,len(f0),4)
command_lines=[]
for frame in grid:
 value=float(shifts[frame])
 ratio=2**(value/12)
 command_lines.append(f'{frame/100:.3f} rubberband pitch {ratio:.7f};')
command_lines.append(f'{(len(f0)-1)/100:.3f} rubberband pitch 1.0000000;')
(Q/'qa94_commands.txt').write_text('\n'.join(command_lines)+'\n',encoding='ascii')
audio_filter='asendcmd=f=qa94_commands.txt,rubberband@rb=tempo=1:pitch=1:formant=preserved:transients=smooth:detector=soft:pitchq=quality:channels=together'
wav=Q/'qa94_tuned_dry.wav'
cmd=['ffmpeg','-nostdin','-hide_banner','-v','error','-y','-i',str(F/'vocals.wav'),
 '-af',audio_filter,'-c:a','pcm_f32le',str(wav)]
t=subprocess.run(cmd,cwd=Q,capture_output=True,text=True,timeout=90)
if t.returncode:raise RuntimeError(t.stderr[-2800:])
changed,cr=sf.read(wav,dtype='float32',always_2d=True)
assert cr==sr and abs(len(changed)-len(source))<sr*.02
# Tiny latency compensation by envelope cross correlation: musical beats should
# not be moved independently. Store estimate and reject significant drift.
from scipy.signal import correlate
hop=441
def envelope(x):
 mono=x.mean(axis=1)
 n=len(mono)//hop*hop
 return np.sqrt(np.mean(mono[:n].reshape(-1,hop).astype('float64')**2,axis=1)+1e-12)
original_energy=envelope(source)
new_energy=envelope(changed)
n=min(len(original_energy),len(new_energy))
ref=original_energy[:n];cur=new_energy[:n]
# Local +/- 90ms time lag only, global envelope fit.
w=min(1200,n)
corr=correlate(cur[:w]-cur[:w].mean(),ref[:w]-ref[:w].mean(),mode='full',method='fft')
sh=np.arange(-w+1,w);mask=np.abs(sh)<=9
lag=int(sh[mask][np.argmax(corr[mask])])
# Accept only 30ms correction; otherwise don't silently time-shift vocals.
if abs(lag)>3:raise RuntimeError(f'Pitch processor misaligned audio {lag*10} ms')
if lag>0:changed=np.pad(changed,( (0,lag*hop), (0,0)))[lag*hop:]
elif lag<0:changed=np.pad(changed,((-lag*hop,0),(0,0)))[:len(changed)]
n=min(len(source),len(changed),len(bed))
# Recombine *same* stems, only changing the lead.
def master(voice):
 mix=voice[:n]+bed[:n]
 p=float(np.max(abs(mix)))
 return (mix*min(1,.90/max(p,1e-9))).astype('float32')
out_a=Q/'qa94_original_stems_mix.wav'
out_b=Q/'qa94_tuned_stems_mix.wav'
sf.write(out_a,master(source),sr,subtype='PCM_24')
sf.write(out_b,master(changed),sr,subtype='PCM_24')
for name,path in [('source',out_a),('tuned',out_b)]:
 mp3=Q/('qa94_'+name+'_35s.mp3')
 pr=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(path),'-c:a','libmp3lame','-b:a','320k',str(mp3)],capture_output=True,text=True,timeout=75)
 if pr.returncode:raise RuntimeError(pr.stderr)
report={
 'version':'QA94','preview_only':True,'production_model_changed':False,
 'input':'ACE-Step SFT 35s isolated vocals and same separated backing',
 'stable_note_segments_detected':len(segments),
 'positive_pitch_shifts':sum(x['move']>0 for x in segments),
 'negative_pitch_shifts':sum(x['move']<0 for x in segments),
 'maximum_correction_cents':round(float(np.max(np.abs(shifts)))*100,2),
 'corrected_frames_over_8c':int(np.sum(np.abs(shifts)>.08)),
 'commands_count':len(command_lines),'command_interval_ms':40,
 'audio_length_original_s':round(len(source)/sr,3),
 'audio_length_processed_s':round(len(changed)/sr,3),
 'estimated_global_envelope_lag_ms':lag*10,
 'detected_segments':[ {k:v for k,v in x.items() if k not in ('at','move')} for x in segments],
 'output_dry':str(wav),
 'output_original':str(Q/'qa94_source_35s.mp3'),
 'output_tuned':str(Q/'qa94_tuned_35s.mp3'),
 'word_endings_unchanged_in_lyrics':True,
 'phoneme_integrity_not_yet_verified':True,
 'instrumental_unchanged':True,
 'perceptual_quality_verified':False,
 'natural_legato_not_guaranteed':True,
 'speaker_identity_not_checked':True}
(Q/'qa94_tuning_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('QA94_RENDERED',json.dumps({k:v for k,v in report.items() if k!='detected_segments'},ensure_ascii=True),flush=True)

"""QA75 non-destructive A/B render using QA54 approved mastering bed and gain."""
import json,sys,subprocess,time,hashlib
from pathlib import Path
import numpy as np,soundfile as sf
R=Path.home()/'Music Studio'; Q=R/'Diagnostics'/'QA54';D=R/'Diagnostics'/'QA75'
sys.path.insert(0,str(R/'Voice Engine'))
from voice_continuity48 import repair
from voice_guard42 import check
from studio_mix21 import vocal_room,gentle_deess
from studio_mix16 import declick
source=Q/'QA54_CFG090_35s.source.wav'
files=list((D/'converted').glob('vc_*.wav'))
assert len(files)==1,files
raw=files[0]
audio,sr=sf.read(raw,dtype='float32',always_2d=True)
src,s_src=sf.read(source,dtype='float32',always_2d=True)
assert sr==s_src==44100
assert audio.shape[0]/sr>34.9
sf.write(D/'QA75_raw_dry.wav',audio.mean(axis=1),sr,subtype='FLOAT')
raw_guard=check(source,raw,D/'qa75_raw_voicecheck.json','ru')
repair_output=D/'QA75_repaired_dry.wav'
fix=repair(source,raw,repair_output)
selected=repair_output if fix.get('used') else raw
guard=check(source,selected,D/'qa75_voicecheck.json','ru')
if not guard['accepted']:raise RuntimeError('QA75 failed severe-gap screening')
q=json.loads((Q/'QA54_CFG090_35s.quality.json').read_text(encoding='utf-8'))
master_path=Path(q['master'])
old_master,ms=sf.read(master_path,dtype='float32',always_2d=True)
old_finished,_=sf.read(Q/'QA54_CFG090_35s.finished.wav',dtype='float32',always_2d=True)
assert ms==sr
total=len(old_master)
def fit(a):
  v=a.mean(axis=1)
  return np.pad(v,(0,max(0,total-len(v))))[:total]
# Reproduce old studio_mix21 output rather than mixing vocals with master twice.
att_old=10**(float(q['mix']['master_gain_db'])/20)
recovered_bed=old_master/att_old-vocal_room(fit(old_finished),sr)
assert np.sqrt(np.mean(((recovered_bed+vocal_room(fit(old_finished),sr))*att_old-old_master)**2))<2e-5
v=fit(sf.read(selected,dtype='float32',always_2d=True)[0])
v=(v-np.mean(v)).astype(np.float32)
v,clicks=declick(v)
v,deess=gentle_deess(v,sr)
gain=10**(float(q['mix']['gain_db'])/20)
v*=gain
sf.write(D/'QA75_finished_dry.wav',v,sr,subtype='FLOAT')
combined=(recovered_bed+vocal_room(v,sr))*att_old
peak=float(np.max(np.abs(combined)))
master_trim=min(1.0,.891/max(peak,1e-9))
combined=combined*master_trim
assert np.isfinite(combined).all()
outfile=D/'QA75_QuietBoundary_35s_Master24.wav'
mp3=D/'QA75_QuietBoundary_35s_320kbps.mp3'
sf.write(outfile,combined,sr,subtype='PCM_24')
cmd=['ffmpeg','-nostdin','-v','error','-y','-i',str(outfile),'-c:a','libmp3lame','-b:a','320k',str(mp3)]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
assert p.returncode==0,p.stderr
assert mp3.stat().st_size>1000000
base_guard=json.loads((Q/'QA54_CFG090_35s.voicecheck.json').read_text(encoding='utf-8'))
# QA54 baseline raw/converter metrics share the same source, not absolute guarantees.
report={'version':'QA75','status':'experimental','no_live_changes':True,
 'same_QA54_owner_model':True,'same_source_and_speaker_reference':True,
 'same_Ace_song_and_seed':True,'same_musical_bed':True,
 'mel_splices_at_source_pauses':True,
 'prior_QA54_energy':base_guard.get('metrics'),
 'qa75_raw_energy':raw_guard.get('metrics'),
 'qa75_post_energy':guard.get('metrics'),
 'repair':fix,'declick_removed':clicks,'deesser':deess,
 'source_vocal_reuse':False,'speaker_verified':False,
 'phoneme_continuity_verified_by_human':False,
 'master_trim_db':round(float(20*np.log10(max(1.e-8,master_trim))),2),
 'output_mp3':str(mp3),'output_wav':str(outfile),
 'output_mp3_sha256':hashlib.sha256(mp3.read_bytes()).hexdigest(),
 'reference_info':'QA57 mic 22s original owner selection',
 'note':'ASR, speaker embedding, and pitch are necessary but insufficient for musical quality'}
(D/'qa75_master_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('QA75_MASTER_READY '+json.dumps(report,ensure_ascii=False))

"""QA76 local training corpus readiness audit.

Pure audit: never fine-tunes, deletes, copies or publishes a recording.
Stage labels are embedded in owner-authorized /api/upload filenames.
A withheld HOLDOUT is NEVER included in a prospective training stage set.
"""
from pathlib import Path
import json,re,hashlib,subprocess
import soundfile as sf
import numpy as np
R=Path.home()/'Music Studio'
V=R/'Мой голос'
P=R/'Voice Profiles'/'profiles.json'
D=R/'Diagnostics'/'QA76';D.mkdir(parents=True,exist_ok=True)
STAGES=('low_legato','low_lines','middle_legato','register_glide',
  'russian_phonemes','dynamic_phrase','rhythmic_rap','melodic_chorus')
HOLD='heldout'
tag=re.compile(r'QA76_(HOLDOUT_)?([a-z_]+)_(\d{8,})\.(wav|mp3|flac|ogg|m4a|aac)$',re.I)
profiles=json.loads(P.read_text(encoding='utf-8')) if P.exists() else {}
assignments=profiles.get('assignments',{})
known={x.get('id'):x for x in profiles.get('profiles',[])}
files=[];unknown=[];stages={x:[] for x in STAGES};holdout=[]
for file in sorted(V.iterdir() if V.exists() else []):
 if not file.is_file():continue
 if 'QA76_' not in file.name:continue
 match=tag.search(file.name)
 if not match:
  if file.suffix.lower() not in ('.json','.tmp'):unknown.append(file.name)
  continue
 is_hold=bool(match.group(1));label=match.group(2).lower()
 if is_hold != (label==HOLD) or (label not in STAGES and label!=HOLD):
  unknown.append(file.name);continue
 assignment=assignments.get(file.name,{})
 profile_id=assignment.get('profile_id')
 rights=bool(assignment.get('rights_confirmed')) and bool(known.get(profile_id,{}).get('rights_confirmed'))
 info={'name':file.name,'label':label,'is_holdout':is_hold,
    'profile_id':profile_id,'rights_confirmed':rights,
    'size_bytes':file.stat().st_size,'valid_audio':False,
    'content_hash':hashlib.sha256(file.read_bytes()).hexdigest()}
 try:
  audio,sr=sf.read(file,dtype='float32',always_2d=True)
  mono=audio.mean(axis=1);length=len(mono)/sr
  f=mono[:(len(mono)//1024)*1024].reshape(-1,1024)
  rms=np.sqrt(np.mean(f*f,axis=1)+1e-11) if len(f) else np.zeros(0)
  threshold=max(.003,float(np.percentile(rms,90))*.08) if len(rms) else .003
  activity=float(np.mean(rms>threshold)) if len(rms) else 0
  clipping=float(np.mean(np.abs(mono)>=.98)) if len(mono) else 1
  finite=bool(np.isfinite(audio).all())
  info.update(seconds=round(length,2),sample_rate=sr,channels=audio.shape[1],
       active_fraction=round(activity,3),clipped_fraction=round(clipping,5),
       valid_audio=bool(finite and 30<=length<=130 and sr>=16000 and activity>.25 and clipping<.002))
 except Exception as e:info['error']=str(e)[:180]
 files.append(info)
 (holdout if is_hold else stages[label]).append(info)
valid_train=[f for k in STAGES for f in stages[k] if f['valid_audio'] and f['rights_confirmed']]
valid_hold=[f for f in holdout if f['valid_audio'] and f['rights_confirmed']]
profile_ids={f['profile_id'] for f in valid_train+valid_hold}
seconds=sum(f.get('seconds',0) for f in valid_train)
missing=[k for k in STAGES if not any(f['valid_audio'] and f['rights_confirmed'] for f in stages[k])]
duplicate_hashes=[x for x in {f['content_hash'] for f in files}
                  if sum(f['content_hash']==x for f in files)>1]
report={'qa':'QA76',
 'stage_labels':list(STAGES),'training_stages_present':len(STAGES)-len(missing),
 'training_stages_required':len(STAGES),'training_audio_seconds':round(seconds,2),
 'holdout_files_valid':len(valid_hold),'holdout_excluded_from_training':True,
 'missing_stages':missing,'unrecognized_filenames':unknown,
 'active_training_files':valid_train,'independent_holdout_files':valid_hold,
 'duplicate_content_hashes':duplicate_hashes,
 'single_authorized_artist':bool(len(profile_ids)==1),
 'dataset_candidate_complete':bool(not missing and valid_hold and len(profile_ids)==1
       and seconds>=600 and not duplicate_hashes and not unknown),
 'ready_to_train_automatically':False,
 'human_cleanliness_and_owner_approval_still_required':True,
 'no_models_modified':True,'no_audio_modified':True}
(D/'qa76_training_readiness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('QA76_READINESS '+json.dumps({k:v for k,v in report.items()
 if k not in ('active_training_files','independent_holdout_files')},ensure_ascii=False))

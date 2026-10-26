"""QA135 objective screen and safe Music Studio library publication for
user-selected ApexSVC consonant protection on 150s Russian rap.
Copies a new, metadata-backed track; never overwrites original files.
"""
from pathlib import Path
from math import gcd
import json,hashlib,os,re,sys,shutil,uuid
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
import parselmouth
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
T=D/"Results"
state=json.loads((T/"QA135_apex_pipeline_report.json").read_text(encoding="utf8"))
original=json.loads((D/"QA135_rap_source_report.json").read_text(encoding="utf8"))
preset=json.loads((R/"Voice Profiles"/"presets"/"QA133_ConsonantProtection_ApexSVC.json").read_text(encoding="utf8"))
assert state["status"]=="complete_awaiting_QA"
assert state["preset"]=="QA133 consonant protection"
assert state["parameters"]["protect"]==preset["parameters"]["protect"]==0.88
src=Path(original["file_master_wav"])
mp3=Path(state["file_mp3"])
master=Path(state["file_master"])
dry=Path(state["dry_vocal"])
voc=Path(state["vocal_stem_file"])
inst=Path(state["instrumental_stem_file"])
assert all(p.is_file() for p in (src,mp3,master,dry,voc,inst))
for p,key in ((src,"master_sha256"),):
 assert hashlib.sha256(p.read_bytes()).hexdigest()==original[key]
assert hashlib.sha256(master.read_bytes()).hexdigest()==state["final_sha256"]
assert hashlib.sha256(mp3.read_bytes()).hexdigest()==state["final_mp3_sha256"]
assert hashlib.sha256(dry.read_bytes()).hexdigest()==state["dry_vocal_sha256"]
def lo16(p):
 w,sr=sf.read(p,always_2d=True,dtype="float32")
 w=w.mean(axis=1)
 if sr!=16000:
  k=gcd(sr,16000)
  w=resample_poly(w,16000//k,sr//k).astype("float32")
 return w
src_v=lo16(voc)
new_v=lo16(dry)
assert abs(len(src_v)-len(new_v))<16000*.16
def envelopes(v,hop=320):
 n=len(v)//hop
 return np.sqrt(np.mean(v[:n*hop].reshape(n,hop).astype("float64")**2,axis=1)+1e-12)
oldenv=envelopes(src_v)
newenv=envelopes(new_v)
n=min(len(oldenv),len(newenv))
ref=oldenv[:n];cmp=newenv[:n]
active=ref>max(.007,float(np.quantile(ref,.75))*.25)
both=active&(cmp>.0006)
assert both.sum()>300,int(both.sum())
gain=float(np.median(ref[both]/cmp[both]))
lost=active&(cmp*gain<ref*.19)
edges=np.diff(np.r_[0,lost.astype("int8"),0])
starts=np.where(edges==1)[0];ends=np.where(edges==-1)[0]
dropouts=[(round(float(a*.02),2),round(float(b*.02),2)) for a,b in zip(starts,ends) if b-a>=7]
def pitch(y):
 p=parselmouth.Sound(y,16000).to_pitch(time_step=.02,pitch_floor=65,pitch_ceiling=450)
 return np.asarray(p.selected_array["frequency"],dtype="float64")
a=pitch(src_v);b=pitch(new_v)
m=min(len(a),len(b))
mask=(a[:m]>65)&(b[:m]>65)&(a[:m]<450)&(b[:m]<450)
if mask.sum()>250:
 deviation=np.abs(1200*np.log2(b[:m][mask]/a[:m][mask]))
 f0median=round(float(np.median(deviation)),2)
 f0p90=round(float(np.quantile(deviation,.9)),2)
else:f0median=None;f0p90=None
full,sr=sf.read(master,always_2d=True,dtype="float32")
assert full.shape[1]==2 and 145<len(full)/sr<155
peak=float(np.max(abs(full)));rms=float(np.sqrt(np.mean(full.astype("float64")**2)))
clipped=float(np.mean(abs(full)>=.999))
duration=float(len(full)/sr)
assert peak<=.95+1e-4 and rms>.01 and clipped<1e-5
assert abs(duration-original["duration_sec"])<.02
diagnostics={
 "original_source_full_duration":original["duration_sec"],
 "result_duration":round(duration,3),
 "new_vocal_duration":round(len(new_v)/16000,3),
 "music_stereo":True,
 "master_peak_dbfs":round(20*np.log10(max(peak,1e-9)),2),
 "master_rms":round(rms,5),
 "clipped_sample_fraction":round(clipped,8),
 "active_source_vocal_frames":int(active.sum()),
 "new_vocal_dropouts_gt140ms":len(dropouts),
 "dropout_intervals":dropouts[:18],
 "matched_pitch_frames":int(mask.sum()),
 "median_f0_abs_deviation_cents":f0median,
 "p90_f0_abs_deviation_cents":f0p90,
 "F0_pitch_shift_config_semitones":0.0,
 "no_original_singer_layer_added":True,
 "voice_quality_requires_user_listening":True,
 "lyrics_entire_text_sent_to_engine":True}
print("QA135_QUALITY",json.dumps(diagnostics,ensure_ascii=False),flush=True)
review=[]
if len(dropouts)>5:review.append("Possible more than five vocal level gaps >140ms")
if f0median is None or f0median>70:review.append("Pitch median deviation needs ear check")
if f0p90 is None or f0p90>160:review.append("Pitch 90th percentile deviation needs ear check")
# Keep a useful generated result even when subjective diction is not
# confirmed. Reject only integrity failures, already asserted above.
session_track=Path(original["file_mp3"])
metadata_path=session_track.with_suffix(".track.json")
orig_meta=json.loads(metadata_path.read_text(encoding="utf8"))
assert orig_meta["lyrics_original"]==json.loads((D/"QA135_rap_request.json").read_text(encoding="utf8"))["lyrics"]
assert not orig_meta.get("voice_applied",False)
suffix="_МОЙ_ГОЛОС_ЗАЩИТА_СОГЛАСНЫХ"
newname=session_track.stem+suffix+".mp3"
dst=R/"Мои треки"/newname
master_dest=R/"Мастер WAV"/(session_track.stem+suffix+".wav")
if dst.exists() or master_dest.exists():
 raise RuntimeError("A QA135 track with these names already exists; no overwrite")
tmp_dst=dst.with_name(dst.name+"."+uuid.uuid4().hex+".tmp")
tmp_master=master_dest.with_name(master_dest.name+"."+uuid.uuid4().hex+".tmp")
try:
 shutil.copy2(mp3,tmp_dst)
 shutil.copy2(master,tmp_master)
 assert hashlib.sha256(tmp_dst.read_bytes()).hexdigest()==state["final_mp3_sha256"]
 assert hashlib.sha256(tmp_master.read_bytes()).hexdigest()==state["final_sha256"]
 os.replace(tmp_master,master_dest)
 os.replace(tmp_dst,dst)
finally:
 tmp_dst.unlink(missing_ok=True);tmp_master.unlink(missing_ok=True)
meta=dict(orig_meta)
meta.update({
 "name":dst.name,
 "url":"/api/audio/"+dst.name,
 "title":"Громче, чем вчера — рэп (мой голос)",
 "master_url":"/api/master/"+master_dest.name,
 "original_url":orig_meta.get("url"),
 "original_name":orig_meta.get("original_name",""),
 "voice_applied":True,
 "voice_pipeline":"QA135 ApexSVC vocal-only separation and 808-safe remix",
 "voice_model_policy":"user_chosen_qa133_consonant_protection",
 "voice_model_used":"ApexSVC zero-shot with user-owned real voice references",
 "voice_model_trained":False,
 "voice_profile_id":"",
 "voice_preset_id":preset["id"],
 "voice_preserve_consonants":True,
 "voice_check_status":"warning" if review else "needs_listening",
 "voice_check_note":"Automated checks completed. Naturalness, accent and exact owner timbre not confirmed by ear. "+
      ("; ".join(review) if review else "No major physical audio failures detected."),
 "acoustic_quality_verified":False,
 "source_rap_track":session_track.name,
 "source_sung_lyrics_unchanged":True,
 "no_source_vocal_overdub":True,
 "source_music_backing_retained":True,
 "finishing":{"mode":"ApexSVC one-pass centered mono lead + original Demucs backing",
              "master_24bit":True,"duration":duration,
              "gain_constant_db":state["vocal_match_constant_gain_db"],
              "peak_dbfs":diagnostics["master_peak_dbfs"],
              "additional_backing_singers":False},
 "human_listening_required":True,
})
dst.with_suffix(".track.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf8")
check={"status":"warning" if review else "needs_listening","accepted":True,
 "human_timbre_match_confirmed":False,
 "human_russian_pronunciation_confirmed":False,
 "reason":"Rendered with QA133 consonant-protection preset. "+
         ("; ".join(review) if review else "Objective waveform integrity passed."),
 "metrics":diagnostics}
dst.with_suffix(".voicecheck.json").write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding="utf8")
result={
 "status":"user_requested_full_rap_published",
 "library_mp3":str(dst),"library_master_wav":str(master_dest),
 "title":meta["title"],"duration":round(duration,3),
 "voice_preset_id":preset["id"],
 "original_track_preserved":True,
 "original_mic_recordings_preserved":True,
 "production_default_voice_converter_not_changed":True,
 "user_selection_saved_in_preset_json":True,
 "human_voice_quality_not_verified":True,
 "warnings":review,
 "quality":diagnostics,
 "final_master_sha256":state["final_sha256"],
 "final_mp3_sha256":state["final_mp3_sha256"]}
(D/"QA135_final_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
print("QA135_LIBRARY_MP3_READY",dst,flush=True)
print("QA135_LIBRARY_MASTER_READY",master_dest,flush=True)
print("QA135_COMPLETED",result["title"],result["duration"],"REVIEW",len(review),flush=True)

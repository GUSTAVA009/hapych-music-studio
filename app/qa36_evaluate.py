"""Objective QA36 new-generation audio audit, not a substitute for listening.
Checks that requested SFX rendered, master edges, broad dynamic development,
voice pass/fail metadata, stereo field, and peak/clipping. Never delete tracks.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,subprocess,time,sys
R=Path.home()/"Music Studio";DIR=R/"Diagnostics"/"QA36"
songs=sorted((R/"Мои треки").glob("*QA36*.mp3"),key=lambda p:p.stat().st_mtime)
if len(songs)!=2:raise RuntimeError(f"Expected 2 QA36 files; saw {len(songs)}")
reports=[]
for p in songs:
 master=R/"Мастер WAV"/(p.stem+".wav")
 if not master.is_file():raise RuntimeError("Missing WAV master for "+p.name)
 audio,sr=sf.read(str(master),dtype="float32",always_2d=True)
 n=len(audio)
 duration=n/sr
 def rms_db(a):
  if len(a)==0:return -120.
  v=float(np.sqrt(np.mean(np.square(a.astype("float64")))))
  return round(float(20*np.log10(max(1e-10,v))),2)
 def window(start,end):
  return audio[min(n,int(sr*start)):min(n,int(sr*end))]
 blocks=[]
 for sec in range(0,int(duration)-1,5):
  seg=window(sec,min(duration,sec+5))
  if len(seg)<sr:continue
  mid=(seg[:,0]+seg[:,1])/2;side=(seg[:,0]-seg[:,1])/2
  cor=float(np.corrcoef(seg.T)[0,1]) if np.std(seg[:,0])>.00001 else 1.
  blocks.append({"start":sec,"end":sec+5,"rms_dbfs":rms_db(seg),
                 "stereo_correlation":round(cor,3),
                 "side_mid_db":round(rms_db(side)-rms_db(mid),2)})
 peak=round(float(20*np.log10(max(1e-9,np.max(np.abs(audio))))),2)
 clipping=int(np.count_nonzero(np.abs(audio)>.999))
 meta_p=p.with_suffix(".track.json")
 meta=json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
 finish_p=p.with_suffix(".finishing.json")
 finish=json.loads(finish_p.read_text(encoding="utf-8")) if finish_p.exists() else {}
 prod_p=p.with_suffix(".production.json")
 prod=json.loads(prod_p.read_text(encoding="utf-8")) if prod_p.exists() else {}
 sfx=prod.get("effects_applied") or prod.get("sound_effects",{}).get("effects_applied") or []
 missing=prod.get("effects_missing") or []
 metrics={"file":p.name,"master":master.name,"duration":round(duration,3),
  "peak_dbfs":peak,"clipped_samples":clipping,
  "start_rms_200ms":rms_db(window(0,.2)),"end_rms_200ms":rms_db(window(duration-.2,duration)),
  "intro_avg_first_10s":rms_db(window(0,10)),
  "climax_avg_35_75s":rms_db(window(35,75)),
  "ending_avg_last_10s":rms_db(window(max(0,duration-10),duration)),
  "sfx_applied":[{"name":x.get("effect"),"start":x.get("start"),"length":x.get("rendered_seconds")} for x in sfx],
  "sfx_missing":missing,
  "voice_applied":meta.get("voice_applied"),"voice_qa":meta.get("voice_check_status"),
  "finishing":{k:finish.get(k) for k in ["fade_in_seconds","fade_out_seconds","peak_dbfs"]},
  "regions":blocks,
  "actual_russian_diction_verified":False,"backing_vocal_harmonies_verified":False}
 metrics["qa_pass"]=bool(duration>100 and peak<=-.7 and clipping==0 and len(missing)==0 and metrics["end_rms_200ms"]<-45 and len(sfx)>=2)
 reports.append(metrics)
 print(json.dumps({"file":p.name,"qa_pass":metrics["qa_pass"],
    "intro_db":metrics["intro_avg_first_10s"],"epic_mid_db":metrics["climax_avg_35_75s"],
    "outro_db":metrics["ending_avg_last_10s"],"sfx":metrics["sfx_applied"],
    "missing":missing,"peak":peak,"end":metrics["end_rms_200ms"]},ensure_ascii=True),flush=True)
(DIR/"new_audio_quality_report.json").write_text(json.dumps({"tracks":reports,"kind":"objective_mix_checks_only"},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA36_AUDIT_FINISHED",len(reports),"passed",sum(x["qa_pass"] for x in reports))

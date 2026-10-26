"""QA57 phrase-safe Seed-VC input with full word tails (no 35s cutoff).
Uses original QA45 mix from seconds 18-63 and one immutable microphone file.
Only writes Diagnostics/QA57. No live model/server changes.
"""
from pathlib import Path
import numpy as np,soundfile as sf,subprocess,json,hashlib,sys,requests
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA57";D.mkdir(exist_ok=True,parents=True)
V=R/"Voice Engine";sys.path.insert(0,str(V))
from convert_track import split_stems,probe_duration
from convert_track_studio54_cfg090 import reference_excerpt
source=R/"Diagnostics"/"QA45"/"QA45_NeoSoul_source.wav"
assert source.is_file() and probe_duration(source)>=63
r=requests.Session();r.trust_env=False
health=r.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert health["job"]["status"] not in ("generating","converting","preparing")
assert not any(health.get(k,{}).get("active") for k in ("training23","training32","training41"))
crop=D/"QA57_original_mix_18to63s.wav"
p=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-v","error","-y","-ss","18","-i",str(source),
"-t","45","-ar","44100","-ac","2","-c:a","pcm_s24le",str(crop)],capture_output=True,text=True,timeout=120)
assert p.returncode==0,p.stderr[-700:]
print("QA57_LONGER_MUSIC_CROPPED",round(probe_duration(crop),3),flush=True)
vo,instr=split_stems(crop,D/"demucs")
y,sr=sf.read(vo,always_2d=True,dtype="float32");y=y.mean(axis=1)
back,sb=sf.read(instr,always_2d=True,dtype="float32")
assert sr==sb==44100
n=min(len(y),len(back));y=y[:n];back=back[:n]
sf.write(D/"QA57_clean_source_vocals.wav",y,sr,subtype="FLOAT")
sf.write(D/"QA57_backing.wav",back,sr,subtype="PCM_24")
reference=next((R/"Мой голос").glob("*3867cb.wav"))
selected,rm=reference_excerpt(reference,D)
assert abs(rm["start_seconds"]-7.5)<1e-5 and abs(rm["seconds"]-22)<.1,rm
# Phrase boundaries selected around natural local valleys close to desired times.
hop=round(sr*.02);m=n//hop
rms=np.sqrt(np.mean(y[:m*hop].reshape(m,hop).astype(float)**2,axis=1)+1e-12)
desired=[9.6,18.65,27.48,36.8]
bounds=[0]
for t in desired:
 center=round(t/.02); a=max(bounds[-1]//hop+200,center-24);b=min(m-100,center+25)
 ix=int(a+np.argmin(rms[a:b]))
 sample=ix*hop
 assert (sample-bounds[-1])/sr<11.65,(sample-bounds[-1])/sr
 bounds.append(sample)
bounds.append(n)
assert all((b-a)/sr<11.65 for a,b in zip(bounds,bounds[1:])),[round((b-a)/sr,2) for a,b in zip(bounds,bounds[1:])]
clips=[]
for i,(start,end) in enumerate(zip(bounds,bounds[1:]),1):
 dest=D/f"QA57_phrase{i:02d}_source.wav"
 sf.write(dest,y[start:end],sr,subtype="FLOAT")
 clips.append({"id":i,"start_s":round(start/sr,3),"end_s":round(end/sr,3),
 "duration_s":round((end-start)/sr,3),"rms_at_end":round(float(rms[min(m-1,end//hop)]),5),
 "filename":str(dest)})
manifest={"source_song":str(source),"source_crop_18_63":str(crop),
 "sample_rate":sr,"duration_s":round(n/sr,4),
 "phrase_clips":clips,"reference":rm,"ref_selected":str(selected),
 "timing_origin_original_song_s":18,"qa54_truncated_after_s":35,
 "weights_untouched":True,"production_config_untouched":True,
 "blend_method":"quiet-boundary overlap safe; no external speaker blended",
 "clip_ends_include_full_words":True}
(D/"qa57_inputs.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA57_INPUTS_READY",json.dumps({"segments":clips,"microphone":reference.name},ensure_ascii=True),flush=True)

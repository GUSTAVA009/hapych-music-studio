from pathlib import Path
import json,subprocess,hashlib,datetime
import numpy as np
ROOT=Path.home()/"Music Studio"
TRACKS=ROOT/"Мои треки"
D=ROOT/"Diagnostics"/"AUTO_QA33";D.mkdir(parents=True,exist_ok=True)
files=sorted(TRACKS.glob("*.mp3"),key=lambda f:f.stat().st_mtime,reverse=True)[:12]
results=[]
for f in files:
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,bit_rate","-of","json",str(f)],capture_output=True,text=True,timeout=20)
    try:probe=json.loads(p.stdout)["format"]
    except Exception as e:results.append({"file":f.name,"error":str(e)});continue
    duration=float(probe["duration"])
    chunks=[]
    for start in (5,25,min(75,max(5,duration-9))):
        p=subprocess.run(["ffmpeg","-v","error","-nostdin","-ss",str(start),"-i",str(f),"-t","4","-ar","16000","-ac","2","-f","f32le","pipe:1"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        if p.returncode or not p.stdout:continue
        z=np.frombuffer(p.stdout,dtype="<f4").reshape(-1,2)
        rms=np.sqrt(np.mean(z.astype("float64")**2,axis=0)+1e-16)
        mid=(z[:,0]+z[:,1])*.5;side=(z[:,0]-z[:,1])*.5
        side_to_mid=20*np.log10((np.sqrt(np.mean(side**2))+1e-8)/(np.sqrt(np.mean(mid**2))+1e-8))
        corr=np.corrcoef(z.T)[0,1] if len(z)>200 else 1.
        chunks.append({"at_s":start,"rms_dbfs":round(float(20*np.log10(float(np.mean(rms))+1e-10)),2),"peak_dbfs":round(float(20*np.log10(max(float(np.max(np.abs(z))),1e-9))),2),"side_mid_db":round(float(side_to_mid),2),"stereo_corr":round(float(corr),3)})
    side=f.with_suffix(".track.json")
    meta={}
    if side.exists():
        try:meta=json.loads(side.read_text(encoding="utf-8"))
        except Exception:pass
    results.append({"file":f.name,"duration_s":round(duration,2),"bitrate":int(probe.get("bit_rate",0)),"metrics":chunks,"voice_applied":meta.get("voice_applied"),"voice_check_status":meta.get("voice_check_status"),"prompt_len":len(str(meta.get("caption_sent") or "")),"size_mb":round(f.stat().st_size/1048576,1)})
report={"created":datetime.datetime.now().isoformat(),"qa":"short excerpt meter, NOT human listening or lyrics quality","tracks":results}
(D/"latest_tracks_before.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
for x in results:print(x["file"][:44],"DURATION",x.get("duration_s"),"VOICE",x.get("voice_applied"),"STATUS",x.get("voice_check_status"),"CHUNKS",x.get("metrics",[])[:2],flush=True)
print("ANALYZED",len(results),"RESULT",str(D/"latest_tracks_before.json"))

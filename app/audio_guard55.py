"""Check ACE-Step audio *before* voice conversion. Avoid publishing DC-dominated noise as music.
No mutation: probes 8 seconds in three parts of the output with ffmpeg (mono PCM).
"""
import subprocess
import numpy as np

def inspect_source(path):
    results=[]
    for offset in (5,30,80):
        proc=subprocess.run(
            ["ffmpeg","-v","error","-nostdin","-ss",str(offset),"-i",str(path),
             "-t","5","-ac","1","-ar","8000","-f","f32le","pipe:1"],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
        if proc.returncode or not proc.stdout:
            if offset>5: continue
            raise RuntimeError("Не удалось проверить исходную музыку: "+proc.stderr.decode("utf-8","replace")[:150])
        y=np.frombuffer(proc.stdout,dtype="<f4")
        if len(y)<8000:continue
        mean=float(y.mean());rms=float(np.sqrt(np.mean(y*y)));ac=float(np.std(y))
        if not np.isfinite(rms) or not np.isfinite(ac):raise RuntimeError("Аудиосигнал содержит некорректные значения.")
        dc=100*mean*mean/(rms*rms+1e-12)
        results.append(dict(t=offset,dc_percent=round(dc,2),ac_rms=round(ac,4),mean=round(mean,4)))
    if not results:raise RuntimeError("Недостаточно аудиоданных для проверки.")
    # Strong DC in multiple independently sampled portions is not normal musical content.
    if sum(a["dc_percent"]>80 for a in results)>=2:
        raise RuntimeError("Генератор вернул испорченный аудиосигнал: постоянное смещение более 80% мощности. Генерация отклонена; некорректный звук не публикуется. Перезапусти музыкальную модель и создай трек заново.")
    if all(a["ac_rms"]<0.0005 for a in results):
        raise RuntimeError("Музыкальный генератор вернул практически тишину.")
    return results

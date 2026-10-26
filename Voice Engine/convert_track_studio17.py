"""Music Studio identity-preserving conversion; originals are never overwritten."""
import argparse, json, os, shutil, subprocess, sys, time, uuid
from pathlib import Path
import numpy as np
import soundfile as sf
from convert_track import ROOT, HERE, VOICE, PYTHON, WIP, say, execute, probe_duration, split_stems
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def reference_excerpt(reference, work):
    # One selected recording only. No concatenation with other speakers/takes.
    decoded=work/'reference_full.wav'
    execute(['ffmpeg','-v','error','-nostdin','-y','-i',reference,'-t','90','-map','0:a:0','-ac','1','-ar','44100','-c:a','pcm_f32le',decoded],label='Decode selected reference')
    y,sr=sf.read(decoded,dtype='float32')
    if y.ndim!=1 or len(y)<sr*2: raise ValueError('Нужна запись голоса длиннее двух секунд.')
    y=y-np.mean(y)
    window=min(len(y),sr*12)
    hop=sr//2
    best=(float('-inf'),0)
    for start in range(0,max(1,len(y)-window+1),hop):
        x=y[start:start+window]
        frames=x[:len(x)//441*441].reshape(-1,441)
        rms=np.sqrt(np.mean(frames*frames,axis=1)+1e-12)
        threshold=max(0.001, float(np.percentile(rms,90))*0.08)
        active=float(np.mean(rms>threshold))
        clipping=float(np.mean(np.abs(x)>=0.99))
        score=active-5*clipping
        if score>best[0]: best=(score,start)
    start=best[1]; x=y[start:start+window]
    peak=float(np.max(np.abs(x)))
    rms=float(np.sqrt(np.mean(x*x)+1e-12))
    if peak<0.001: raise ValueError('В выбранной записи почти нет слышимого сигнала.')
    gain=min(10**(12/20),10**(-23/20)/max(rms,1e-9),0.85/max(peak,1e-9))
    out=work/'reference_selected.wav'
    sf.write(out,x*gain,sr,subtype='FLOAT')
    return out,{'source':str(reference),'start_seconds':start/sr,'seconds':len(x)/sr,'gain_db':round(float(20*np.log10(gain)),2),'merged_recordings':False}

def finish_mix(vocal,backing,source_vocal,output,duration,work):
    from studio_mix16 import finish
    master_dir=ROOT/'Мастер WAV';master_dir.mkdir(exist_ok=True)
    master=master_dir/(output.stem+'.wav');partial=master.with_suffix('.part.wav')
    report=finish(vocal,backing,source_vocal,work/'vocal_finished.wav',partial)
    partial.replace(master)
    execute(['ffmpeg','-v','error','-nostdin','-y','-i',master,'-c:a','libmp3lame','-b:a','320k',output],label='MP3 listening copy')
    return master,report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True); p.add_argument('--voice',required=True);p.add_argument('--output',required=True)
    p.add_argument('--steps',type=int,default=32);p.add_argument('--trained',action='store_true')
    p.add_argument('--register',choices=['auto','original','lower'],default='auto')
    p.add_argument('--pitch-smooth',type=float,default=0) # legacy caller compatibility, intentionally unused
    p.add_argument('--seed',type=int,default=74191);p.add_argument('--keep-dry',action='store_true')
    a=p.parse_args(); source=Path(a.source).resolve(); reference=Path(a.voice).resolve(); output=Path(a.output).resolve()
    if not source.is_file() or not reference.is_file():raise FileNotFoundError('Не найден трек или выбранная запись голоса.')
    if output in (source,reference):raise ValueError('Исходные файлы нельзя перезаписывать.')
    if not 8<=a.steps<=60:raise ValueError('Количество шагов должно быть 8–60.')
    output.parent.mkdir(parents=True,exist_ok=True)
    work=WIP/('identity_'+uuid.uuid4().hex[:12]);work.mkdir()
    started=time.monotonic()
    try:
        seconds=probe_duration(source)
        if not 2<=seconds<=610:raise ValueError('Длительность трека должна быть 2–610 секунд.')
        say('Готовим только выбранный образец голоса...')
        target,ref_meta=reference_excerpt(reference,work)
        vocals,backing=split_stems(source,work/'stems')
        converted=work/'converted';converted.mkdir()
        command=[PYTHON,'inference_studio17.py','--source',vocals,'--target',target,'--output',converted,'--diffusion-steps',str(a.steps),'--f0-condition','True','--fp16','True','--auto-f0-adjust','False','--semi-tone-shift','0','--register',a.register,'--seed',str(a.seed)]
        if a.trained:
            folder=VOICE/'runs'/'music_studio_personal_v1'
            checkpoint=folder/'ft_model.pth'
            config=folder/'config_dit_mel_seed_uvit_whisper_base_f0_44k.yml'
            if not checkpoint.is_file() or not config.is_file():raise FileNotFoundError('Не найдена персональная модель с её конфигурацией.')
            command += ['--checkpoint',checkpoint,'--config',config]
        say('Сохраняем непрерывность вокала; без переключений регистра между фразами...')
        execute(command,cwd=VOICE,label='Identity voice '+('trained' if a.trained else 'base'))
        files=list(converted.glob('vc_*.wav'))
        if len(files)!=1:raise RuntimeError('Голосовой движок не вернул одну вокальную дорожку.')
        say('Убираем резкие сибилянты и выравниваем баланс вокала с музыкой...')
        master,mix_report=finish_mix(files[0],backing,vocals,output,seconds,work)
        report=json.loads((converted/'register_report.json').read_text(encoding='utf-8'))
        report.update(mix=mix_report,reference_preparation=ref_meta,model='personal' if a.trained else 'base',diffusion_steps=a.steps,seed=a.seed,elapsed_seconds=round(time.monotonic()-started,2),master=str(master),source_file=str(source),final=str(output))
        output.with_suffix('.quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if a.keep_dry:
            sfdata,sr=sf.read(files[0],dtype='float32');sf.write(output.with_suffix('.dry.wav'),sfdata,sr,subtype='FLOAT')
            shutil.copy2(work/'vocal_finished.wav',output.with_suffix('.finished.wav'))
            shutil.copy2(vocals,output.with_suffix('.source.wav'))
        print('RESULT:'+json.dumps(report,ensure_ascii=True),flush=True)
        say('Готово. Итоговый трек и отдельный мастер сохранены.')
    finally:
        shutil.rmtree(work,ignore_errors=True)
if __name__=='__main__':main()

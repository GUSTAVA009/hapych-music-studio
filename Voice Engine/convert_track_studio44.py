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
    window=min(len(y),sr*22)
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
    length_seconds=len(y)/sr
    short=length_seconds<15.
    return out,{'source':str(reference),'start_seconds':start/sr,'seconds':len(x)/sr,
                'total_recording_seconds':round(length_seconds,3),
                'gain_db':round(float(20*np.log10(gain)),2),
                'merged_recordings':False,
                'short_reference_warning':short,
                'warning':('Референс голоса короче 15 секунд. Для качественного тембра рекомендована чистая речь 20-40 секунд без музыки.' if short else ''),
                'voice_cleanliness_verified':False}

def finish_mix(vocal,backing,source_vocal,output,duration,work,chorus_ranges=None):
    from studio_mix21 import finish
    master_dir=ROOT/'Мастер WAV';master_dir.mkdir(exist_ok=True)
    master=master_dir/(output.stem+'.wav');partial=master.with_suffix('.part.wav')
    report=finish(vocal,backing,source_vocal,work/'vocal_finished.wav',partial,chorus_ranges=chorus_ranges)
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
    p.add_argument('--language',default='unknown')
    p.add_argument('--chorus-ranges',default='[]')
    a=p.parse_args(); source=Path(a.source).resolve(); reference=Path(a.voice).resolve(); output=Path(a.output).resolve()
    chorus_ranges=json.loads(a.chorus_ranges)
    if not isinstance(chorus_ranges,list) or len(chorus_ranges)>60 or any(not isinstance(item,list) or len(item)!=2 or any(not isinstance(t,(int,float)) or not np.isfinite(t) or t<0 or t>610 for t in item) or item[1]<=item[0] for item in chorus_ranges):
        raise ValueError('Invalid chorus regions')
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
        if ref_meta.get('short_reference_warning'):
            say('Внимание: референс слишком короткий; качество переноса тембра может ухудшиться.')
        vocals,backing=split_stems(source,work/'stems')
        converted=work/'converted';converted.mkdir()
        command=[PYTHON,'inference_studio17.py','--source',vocals,'--target',target,'--output',converted,'--diffusion-steps',str(a.steps),'--f0-condition','True','--fp16','True','--auto-f0-adjust','False','--semi-tone-shift','0','--register',a.register,'--seed',str(a.seed)]
        if a.trained:
            folder=VOICE/'runs'/'alex_clean_qa44_v2'
            checkpoint=folder/'ft_model.pth'
            config=folder/'config_dit_mel_seed_uvit_whisper_base_f0_44k.yml'
            if not checkpoint.is_file() or not config.is_file():raise FileNotFoundError('Не найдена персональная модель с её конфигурацией.')
            command += ['--checkpoint',checkpoint,'--config',config]
        say('Сохраняем непрерывность вокала; без переключений регистра между фразами...')
        execute(command,cwd=VOICE,label='Identity voice '+('trained' if a.trained else 'base'))
        # The low-level decoder may produce audio despite an octave shift or
        # collapsed vocal. Do not publish it as the user's voice if multiple
        # independent song windows show severe regression.
        preliminary = json.loads((converted/'register_report.json').read_text(encoding='utf-8'))
        pitch_check = preliminary.get('pitch_consistency', {})
        if pitch_check.get('status') == 'rejected':
            diagnostic = {'status':'rejected', 'accepted':False,
                          'reason':pitch_check['reason'], 'pitch_consistency':pitch_check,
                          'speaker_similarity_verified':False,
                          'perceptual_quality_verified':False}
            output.with_suffix('.voicecheck.json').write_text(
                json.dumps(diagnostic,ensure_ascii=False,indent=2),encoding='utf-8')
            print('VOICE_REJECTED:'+pitch_check['reason'],flush=True)
            raise RuntimeError(pitch_check['reason'])
        files=list(converted.glob('vc_*.wav'))
        if len(files)!=1:raise RuntimeError('Голосовой движок не вернул одну вокальную дорожку.')
        say('Проверяем непрерывность вокала и мягко восстанавливаем короткие перепады уровня...')
        from voice_continuity42 import repair
        from voice_guard42 import check
        original_converted=files[0]
        continuity_info=repair(vocals,original_converted,work/'continuity42.wav')
        selected_vocal=work/'continuity42.wav' if continuity_info.get('used') else original_converted
        voice_check=check(vocals,selected_vocal,output.with_suffix('.voicecheck.json'),a.language)
        if pitch_check.get('status') == 'review' and voice_check['accepted']:
            # Surface a suspicious pitch interval instead of claiming clean QA.
            voice_check['status'] = 'warning'
            voice_check['reason'] = pitch_check['reason'] + ' ' + voice_check['reason']
            voice_check['pitch_consistency'] = pitch_check
            output.with_suffix('.voicecheck.json').write_text(
                json.dumps(voice_check,ensure_ascii=False,indent=2),encoding='utf-8')
        if not voice_check['accepted']:
            print('VOICE_REJECTED:'+voice_check['reason'],flush=True)
            raise RuntimeError(voice_check['reason'])
        if ref_meta.get('short_reference_warning'):
            voice_check['status']='warning'
            voice_check['reason']=str(voice_check.get('reason',''))+' '+ref_meta['warning']
            output.with_suffix('.voicecheck.json').write_text(
                json.dumps(voice_check,ensure_ascii=False,indent=2),encoding='utf-8')
        say('Сохраняем чёткость согласных и добавляем мягкую студийную глубину без изменения фонем...')
        master,mix_report=finish_mix(selected_vocal,backing,vocals,output,seconds,work,chorus_ranges=chorus_ranges)
        report=json.loads((converted/'register_report.json').read_text(encoding='utf-8'))
        report.update(pipeline_revision='voice_guard42_continuity42_pitch_clean51_stereo_mix21',voice_check=voice_check,continuity=continuity_info,mix=mix_report,reference_preparation=ref_meta,model='personal' if a.trained else 'base',diffusion_steps=a.steps,seed=a.seed,elapsed_seconds=round(time.monotonic()-started,2),master=str(master),source_file=str(source),final=str(output))
        output.with_suffix('.quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if a.keep_dry:
            sfdata,sr=sf.read(selected_vocal,dtype='float32');sf.write(output.with_suffix('.dry.wav'),sfdata,sr,subtype='FLOAT')
            shutil.copy2(work/'vocal_finished.wav',output.with_suffix('.finished.wav'))
            shutil.copy2(vocals,output.with_suffix('.source.wav'))
        print('RESULT:'+json.dumps(report,ensure_ascii=True),flush=True)
        say('Готово. Итоговый трек и отдельный мастер сохранены.')
    finally:
        shutil.rmtree(work,ignore_errors=True)
if __name__=='__main__':main()

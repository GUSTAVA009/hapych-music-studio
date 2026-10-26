"""QA88: source-vocal comparison of local, isolated Turbo vs SFT samples.

Measures transcription as an approximate signal only; doesn't 'certify' Russian
phonemes, timbre or natural singing. Never mutates original tracks/models.
"""
from pathlib import Path
import sys,os,json,subprocess,re,time,shutil
import numpy as np,torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA86-SFTBenchmark'
DATA={
 'SFT':D/'sft_35s.wav',
 'Turbo':D/'turbo_35s.wav'
}
D.mkdir(parents=True,exist_ok=True)
assets=R/'Diagnostics'/'rejected-light-audit'/'whisper_text_assets'
base=R/'Voice Engine'/'seed-vc'/'checkpoints'/'hf_cache'/'models--openai--whisper-small'/'snapshots'/'973afd24965f72e36ca33b3055d56a652f456b4d'
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
LYRICS="""[Verse]
Ты меня тихо найдёшь,
Все слова произнесёшь.
Снова рядом подойдёшь,
Песню мне одну споёшь.

[Chorus]
Ты найдёшь, ты найдёшь,
И меня ты позовёшь.
Дай, дай, дай мне ладонь,
Снова музыка, огонь!

[Outro]
Ты меня найдёшь.
"""
expected=' '.join(line.strip() for line in LYRICS.splitlines() if line.strip() and not line.startswith('['))
exp_words=re.findall(r'[а-яё]+',expected.lower().replace('ё','е'))
def transcript(m,p,path):
 audio=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(path),
  '-ac','1','-ar','16000','-f','f32le','pipe:1'],capture_output=True,check=True,timeout=70).stdout
 wave=np.frombuffer(audio,dtype='<f4').copy()
 spans=[wave[:int(27*16000)],wave[int(27*16000):]]
 texts=[]
 for z in spans:
  if len(z)<8000:continue
  sample=p(z,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
  with torch.inference_mode():
   ids=m.generate(**sample,task='transcribe',language='ru',do_sample=False,num_beams=1,max_new_tokens=160)
  texts.append(p.batch_decode(ids,skip_special_tokens=True)[0])
 return ' '.join(texts)
def edit(a,b):
 row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  n=[i]
  for j,y in enumerate(b,1):n.append(min(n[-1]+1,row[j]+1,row[j-1]+(x!=y)))
  row=n
 return row[-1]
def tokens(text):return re.findall(r'[а-яё]+',text.lower().replace('ё','е'))
def separate(name,path):
 folder=D/(name.lower()+'_stems')
 dest=folder/'htdemucs'/path.stem/'vocals.wav'
 if dest.is_file():return dest
 if not path.is_file():return None
 print('SEPARATING_VOCALS',name,flush=True)
 command=[str(R/'Voice Engine'/'.venv'/'Scripts'/'python.exe'),'-m','demucs',
 '-n','htdemucs','--two-stems=vocals','-d','cuda','--segment','7','-o',str(folder),str(path)]
 with (D/(name.lower()+'_demucs.log')).open('w',encoding='utf-8') as log:
  ret=subprocess.run(command,cwd=str(R/'Voice Engine'),stdout=log,stderr=subprocess.STDOUT,timeout=500)
 if ret.returncode or not dest.exists():
  print('SEPARATION_FAILED',name,'falling back to mixed song',flush=True)
  return path
 return dest
def main():
 files={k:p for k,p in DATA.items() if p.is_file()}
 if not files:raise RuntimeError('No sample files available')
 try:
  live=__import__('requests').get('http://127.0.0.1:7870/api/status',timeout=6).json()
  if live.get('status') in ('generating','converting','preparing'):raise RuntimeError('Studio busy; avoid GPU separation')
 except __import__('requests').exceptions.RequestException:raise RuntimeError('Unable to verify idle studio')
 extracted={k:separate(k,p) for k,p in files.items()}
 print('LOAD_WHISPER_SMALL_CPU',flush=True)
 torch.set_num_threads(4)
 p=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
 model=WhisperForConditionalGeneration.from_pretrained(str(base),local_files_only=True,torch_dtype=torch.float32).eval()
 model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
 model.generation_config.forced_decoder_ids=None
 model.config.forced_decoder_ids=None
 result={'benchmark':'QA88','expected_lyrics':expected,'expected_words':len(exp_words),
 'transcription_is_only_proxy':True,'user_voice_not_evaluated':True,'files':{}}
 for name,path in extracted.items():
  start=time.monotonic()
  text=transcript(model,p,path)
  lex=tokens(text)
  misses={}
  for form in ('найдешь','поймешь','позовешь','произнесешь','подойдешь','споешь'):
   misses[form]={'expected_count':exp_words.count(form),'recognized_count':lex.count(form)}
  edits=edit(exp_words,lex)
  result['files'][name]={'audio_file':str(DATA[name]),'vocal_file':str(path),
    'transcript':text,'recognized_words':len(lex),'word_edit_distance':edits,
    'approx_WER':round(edits/max(1,len(exp_words)),3),
    'word_ending_samples':misses,'asr_s':round(time.monotonic()-start,2)}
  print('ASR',name,json.dumps(result['files'][name],ensure_ascii=True)[:4500],flush=True)
 (D/'qa88_transcription_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('QA88_ASR_FINISHED',flush=True)
if __name__=='__main__':main()

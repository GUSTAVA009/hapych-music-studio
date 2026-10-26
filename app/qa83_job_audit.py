from pathlib import Path
import json,re
R=Path.home()/'Music Studio';job='91ce163d15784ad28efdb30905563c34'
req=R/'app'/'requests'/(job+'.json')
print('REQUEST_EXISTS',req.is_file())
if req.exists():
 d=json.loads(req.read_text(encoding='utf-8'))
 for key in ['voice_routing']:
  print(key,json.dumps(d.get(key),ensure_ascii=True)[:2000])
 prep=d['preparation']
 for key in ['caption','reference_profile','reference_register_instruction','warnings','lyrics_length','music_key']:
  print('PREP_'+key,json.dumps(prep.get(key),ensure_ascii=True)[:2500])
 print('lyrics_sent_len',len(d.get('settings',{}).get('Lyrics','')))
 print('lyrics_sent_wordcount',len(re.findall(r'[А-Яа-яЁё]+',d.get('settings',{}).get('Lyrics',''))))
print('ORIGINAL')
for p in sorted((R/'Исходные версии').glob('*91ce16*')):
 if p.is_file() and p.suffix.lower() in ('.wav','.mp3','.flac','.json'):
  print('FILE',p.name.encode('unicode_escape').decode(),p.stat().st_size)
print('OUTPUTS')
for p in sorted((R/'Мои треки').glob('*91ce16*')):
 if p.is_file():
  print('FILE',p.name.encode('unicode_escape').decode(),p.stat().st_size)
  if p.suffix=='.json' and p.name.endswith('.quality.json'):
   item=json.loads(p.read_text(encoding='utf-8'))
   for k in ['model','register','pitch_consistency','continuity','mix','reference_preparation']:
    print('QUALITY',k,json.dumps(item.get(k),ensure_ascii=True)[:2500])
  if p.suffix=='.json' and p.name.endswith('.voicecheck.json'):
   item=json.loads(p.read_text(encoding='utf-8'))
   print('VOICECHECK',json.dumps(item,ensure_ascii=True)[:3000])

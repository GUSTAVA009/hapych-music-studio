"""Regression scenarios for QA92 asr guard, no real audio or GPU."""
import json,tempfile,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path.home()/'Music Studio'/'Voice Engine'))
import voice_guard92
long=['ты','меня','тихо','найдешь','и','снова','подойдешь','скажешь',
      'что','знаешь','как','поймешь','и','споешь','хорошую','песню','этот','вечер']
cases=[
 ('severe', " ".join(long), "ты меня",False,"rejected_severe_lexical_loss"),
 ('minor'," ".join(long)," ".join(long[:-2]),True,"screened"),
 ('no_words',"музыка припев","речь",True,"insufficient_lyric_content")]
with tempfile.TemporaryDirectory() as folder:
 for name,src,dst,accepted,expected in cases:
  base={'status':'warning','accepted':True,'reason':'some energy dips','metrics':{'relative_missing_vocal_frames':.065}}
  report=Path(folder)/(name+'.json')
  with patch.object(voice_guard92.voice_guard42,'check',return_value=dict(base)):
   with patch.object(voice_guard92,'transcriptions',return_value=(src,dst)):
    data=voice_guard92.check('src.wav','dst.wav',report,language='ru')
  assert data['accepted']==accepted,(name,data)
  assert data['linguistic_gate']==expected,(name,data)
  assert report.exists()
  print('QA92_REGRESSION_OK',name,'accepted',accepted,'status',data['linguistic_gate'],flush=True)
 with patch.object(voice_guard92.voice_guard42,'check',return_value={'status':'rejected','accepted':False}):
  with patch.object(voice_guard92,'transcriptions',side_effect=RuntimeError('should not ASR')):
   q=voice_guard92.check('src.wav','dst.wav',Path(folder)/'reject.json','ru')
   assert q['accepted'] is False and q['linguistic_gate']=='not_run'
 print('QA92_FAIL_CLOSED_TEST_PASS')

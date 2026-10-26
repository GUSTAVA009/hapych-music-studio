from pathlib import Path
from unittest.mock import patch
import sys,subprocess
r=Path.home()/'Music Studio';sys.path.insert(0,str(r/'app'))
import studio_server
logs=r/'Diagnostics'/'QA90-NativeStyle'/'qa91_engine_mock.log'
captured=[]
def fake_popen(args,**kwargs):
 captured.append((args,kwargs))
 class Fake:
  pid=9999999
 return Fake()
with patch.object(studio_server,'engine_ok',return_value=False):
 with patch.object(studio_server,'LOG',logs):
  with patch.object(studio_server.subprocess,'Popen',side_effect=fake_popen):
   studio_server.start_engine()
assert len(captured)==1
args,kwargs=captured[0]
assert args[0].endswith('acestep.exe')
assert args[args.index('--port')+1]=='7862'
assert args[args.index('--config_path')+1]=='acestep-v15-turbo'
assert args[args.index('--lm_model_path')+1]=='acestep-5Hz-lm-1.7B'
assert kwargs['cwd']==str(r/'ACE-Step-1.5')
assert kwargs['env']['NO_PROXY']=='127.0.0.1,localhost,::1'
print('QA91_ENGINE_AUTOSTART_MOCK_PASS',args[1:],'port_7862=True',flush=True)

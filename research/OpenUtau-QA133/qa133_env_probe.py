import sys,importlib.util,os
print("PY",sys.executable,"VERSION",sys.version.split()[0])
for name in ["resampy","torch","torchaudio","fairseq","librosa","pyworld","parselmouth","torchfcpe","fcpe","soundfile","sklearn","numba"]:
 try:print("MODULE",name,bool(importlib.util.find_spec(name)))
 except Exception as e:print("MODULE_ERROR",name,repr(e))

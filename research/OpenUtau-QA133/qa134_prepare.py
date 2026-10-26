from pathlib import Path
root=Path(__file__).parent
src=(root/"qa133_owner_cpu.py").read_text(encoding="utf8")
needle='cases=[("main_identity",{"topk":4,"alpha":.22,"protect":.72,"rms_mix_rate":.92}),\n       ("consonants",{"topk":6,"alpha":.32,"protect":.88,"rms_mix_rate":.95})]'
assert needle in src
src=src.replace(needle,'cases=[("max_consonant",{"topk":4,"alpha":.22,"protect":1.0,"rms_mix_rate":.92})]')
src=src.replace('out=D/"QA133-OwnerVoice"','out=D/"QA134-OwnerVoice"')
src=src.replace('QA133_MyVoice_','QA134_MyVoice_')
src=src.replace('QA133_owner_transfer.json','QA134_owner_transfer.json')
src=src.replace('QA133_OWNER_','QA134_OWNER_')
dst=root/"qa134_max_consonants_cpu.py"
dst.write_text(src,encoding="utf8")
assert 'max_consonant' in dst.read_text(encoding="utf8")
print("QA134_ONE_CASE_PREPARED",dst,flush=True)

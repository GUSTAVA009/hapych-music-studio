"""Fork QA70 into QA73. Apply owner timbre only over sustained voiced vowel regions.
Keep original recording and diffusion checkpoints untouched.
"""
from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
original=(R/"app"/"qa70_timbre_transfer.py").read_text(encoding="utf-8")
assert original.count('D=R/"Diagnostics"/"QA70"')==1
p=original.replace('D=R/"Diagnostics"/"QA70"','D=R/"Diagnostics"/"QA73"')
a='''gate=gaussian_filter1d(active_src.astype(np.float32),sigma=6,mode="nearest")
gate=np.clip(gate,0,1).astype(np.float32)'''
b='''# QA73: direct owner timbre ONLY on stable voiced segments (mostly vowels).
# This leaves consonants and their releases intact, protecting Russian articulation.
from scipy.signal import resample_poly
import os,torch
os.environ["HF_HUB_CACHE"]=str(R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1"
old_cwd=os.getcwd()
os.chdir(str(R/"Voice Engine"/"seed-vc"))
sys.path.insert(0,str(R/"Voice Engine"/"seed-vc"))
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
rmvpe_file=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
rmvpe=RMVPE(rmvpe_file,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
f0=np.asarray(rmvpe.infer_from_audio(resample_poly(x,160,441).astype(np.float32),thred=0.03),dtype=np.float32)
voiced=(f0>70)&(f0<1100)
# F0 at 100Hz; interpolate it to spectral analysis hop (~11.6 ms).
timesteps=np.arange(len(f0))*0.01
sustain=np.interp(ts,timesteps,voiced.astype(np.float32),left=0,right=0)
sustain=gaussian_filter1d(sustain,sigma=.045/time_hop,mode="nearest")
# Prevent the filter from turning on around short pauses.
sustain=np.clip((sustain-.10)/.70,0,1).astype(np.float32)
gate=gaussian_filter1d(active_src.astype(np.float32),sigma=5,mode="nearest")*sustain
gate=np.clip(gate,0,1).astype(np.float32)
os.chdir(old_cwd)
print("QA73_VOWEL_MASK",float(np.mean(gate)),float(np.mean(gate>.6)),flush=True)'''
assert p.count(a)==1
p=p.replace(a,b)
a2='''configs={
  "Mic80_Dyn30":(0.8,0.3,10.0),
  "Mic80_Dyn80":(0.8,0.8,13.0),
  "Mic120_Dyn55":(1.2,0.55,14.0),
  "Mic60_Dyn125":(0.6,1.25,15.0),
}'''
b2='''configs={
  "Vowel_Mic80_Dyn80":(0.8,0.8,13.0),
  "Vowel_Mic120_Dyn55":(1.2,0.55,14.0),
  "Vowel_Mic100_Dyn15":(1.0,0.15,12.0),
}'''
assert p.count(a2)==1
p=p.replace(a2,b2)
p=p.replace('"qa":"QA70"','"qa":"QA73"').replace('qa70_timbre_transfer_report.json','qa73_timbre_transfer_report.json').replace('QA70_','QA73_').replace('QA70_CANDIDATE','QA73_CANDIDATE')
# Document vowel-only gate in report
p=p.replace('"target_recording_directly_used":True,','"target_recording_directly_used":True,\n "vowel_only_F0_mask":True,')
out=R/"app"/"qa73_vowel_timbre.py"
out.write_text(p,encoding="utf-8");py_compile.compile(str(out),doraise=True)
print("QA73_VOWEL_CODE_OK",out)

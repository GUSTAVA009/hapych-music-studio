"""QA58 zero pitch-smoothing control.
Source, timbre identity, checkpoint, CFG, seed, mel decoder, and all other
settings unchanged from QA54. Diagnose whether F0 smoothing destroys syllables.
"""
from pathlib import Path
import py_compile,json,hashlib
R=Path.home()/"Music Studio";S=R/"Voice Engine"/"seed-vc";D=R/"Diagnostics"/"QA58";D.mkdir(exist_ok=True)
p=S/"inference_studio51.py"
src=p.read_text(encoding="utf-8")
old="""        F0_alt, pitch_clean_report = stabilize_f0(
            F0_alt, converted_waves_16k[0].detach().cpu().numpy(), sample_rate=16000)"""
replacement="""        # QA58: diagnostic pass-through, no model/pitch/timbre edits.
        # Intentional: preserve original RMVPE contour including genuine slides.
        pitch_clean_report = {
            "revision": "qa58_raw_rmvpe_contour", "changed_voiced_frames": 0,
            "smoothed_stable_frames": 0, "vibrato_reduced_not_eliminated": False,
            "intentional_register_changes_preserved": True
        }"""
assert src.count(old)==1,src.count(old)
fork=S/"inference_studio58.py"
fork.write_text(src.replace(old,replacement),encoding="utf-8")
py_compile.compile(str(fork),doraise=True)
q={"purpose":"test original raw F0 vs pitch cleaned QA54","inference":str(fork),
   "change":"no stabilize_f0; all other settings identical to QA54",
   "mel_prompt_seconds":18,"style_seconds":22,"cfg":.90,
   "seed":74191,"diffusion_steps":40,"model":"alex_clean_qa44_v2",
   "production_file_untouched":True,
   "old_sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
(D/"qa58_design.json").write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA58_FORK_VERIFIED",json.dumps(q,ensure_ascii=True),flush=True)

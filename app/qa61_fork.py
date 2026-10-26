"""QA61 isolate Seed-VC mel and test vocoder seam hypothesis.
Fork live code once. Does NOT modify app or models.
"""
from pathlib import Path
import py_compile,json,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA61";D.mkdir(parents=True,exist_ok=True)
S=R/"Voice Engine"/"seed-vc"
original=S/"inference_studio51.py"
text=original.read_text(encoding="utf-8")
needle="    joined = canvas / weights[None, None, :]\n    vc_wave = decode_with_context(joined, vocoder_fn, device, hop_length)"
assert text.count(needle)==1
replacement="""    joined = canvas / weights[None, None, :]
    # QA61: serialize EXACT generated log-mel for a separate BigVGAN-only process.
    mel_dump_path = os.environ.get('QA61_MEL_EXPORT_PATH')
    if mel_dump_path:
        from pathlib import Path as _Path
        target = _Path(mel_dump_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save({'mel': joined.detach().float().cpu(),
                    'sample_rate': sr, 'hop_length': hop_length,
                    'reference_identity': target_name, 'seed': args.seed}, target)
        print('QA61_MEL_EXPORT_OK:' + str(target),flush=True)
    vc_wave = decode_with_context(joined, vocoder_fn, device, hop_length)"""
fork=S/"inference_studio61.py"
fork.write_text(text.replace(needle,replacement),encoding="utf-8")
py_compile.compile(str(fork),doraise=True)
metadata={"method":"same diffusion and mel, compare hard chunk joined BigVGAN vs uninterrupted full-mel decode",
"original_script":str(original),"original_sha":hashlib.sha256(original.read_bytes()).hexdigest(),
"fork_script":str(fork),"models_unchanged":True,"production_unchanged":True}
(D/"qa61_experiment.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA61_FORK_READY",json.dumps(metadata,ensure_ascii=True),flush=True)

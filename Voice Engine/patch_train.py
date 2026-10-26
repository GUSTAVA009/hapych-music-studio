from pathlib import Path
root=Path.home()/'Music Studio'/'Voice Engine'/'seed-vc'
src=(root/'train.py').read_text(encoding='utf-8')
patches=[
 ('        self.build_converter(device, config)\n        self.build_vocoder(device, config)','        # Run frozen timbre converter on CPU to fit an 8 GB GPU.\n        self.build_converter("cpu", config)\n        print("Low VRAM: frozen converter on CPU, no unused vocoder", flush=True)'),
 ('self.model.cfm.estimator.setup_caches(max_batch_size=batch_size, max_seq_length=8192)','self.model.cfm.estimator.setup_caches(max_batch_size=batch_size, max_seq_length=2048)'),
 ('        se_batch = self.tone_color_converter.extract_se(waves_22k, wave_lengths_22k)','        with torch.no_grad():\n            se_batch = self.tone_color_converter.extract_se(waves_22k.cpu(), wave_lengths_22k.cpu())'),
 ('        ref_se = self.se_db[ref_se_idx].to(self.device)','        ref_se = self.se_db[ref_se_idx].to("cpu")'),
 ('        converted_waves_22k = self.tone_color_converter.convert(\n            waves_22k, wave_lengths_22k, se_batch, ref_se\n        ).squeeze(1)','        with torch.no_grad():\n            converted_waves_22k = self.tone_color_converter.convert(\n                waves_22k.cpu(), wave_lengths_22k.cpu(), se_batch, ref_se\n            ).squeeze(1).to(self.device)'),
]
for old,new in patches:
 if src.count(old)!=1:
  raise RuntimeError(f'Expected exactly one match, found {src.count(old)}: {old[:55]}')
 src=src.replace(old,new)
dst=root/'train_hapych_lowvram.py'
dst.write_text(src,encoding='utf-8')
print('LOW_VRAM_TRAINER_PREPARED',dst,len(src),flush=True)

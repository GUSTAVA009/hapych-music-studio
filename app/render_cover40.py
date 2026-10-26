"""Dedicated isolated SD-Turbo inference process. Exits after each cover."""
import sys,hashlib,torch
from PIL import Image
from diffusers import StableDiffusionPipeline
from pathlib import Path
if len(sys.argv)<4:raise SystemExit("model, destination, prompt required")
model,out,prompt=sys.argv[1],Path(sys.argv[2]),sys.argv[3]
# Avoid allocating the GPU while a separate, user-requested music LoRA trains.
import json,psutil
lock=Path.home()/"Music Studio"/"Training Runs"/"music41"/"training_reservation.json"
if lock.is_file():
 try:
  reservation=json.loads(lock.read_text(encoding="utf-8"))
  process=psutil.Process(int(reservation["pid"]))
  if process.is_running() and abs(process.create_time()-float(reservation["started"]))<2:
   raise SystemExit("COVER_SKIPPED_GPU_TRAINING_ACTIVE")
 except (psutil.Error,ValueError,KeyError,OSError):pass
pipe=StableDiffusionPipeline.from_pretrained(model,torch_dtype=torch.float16,
    variant="fp16",local_files_only=True,safety_checker=None,requires_safety_checker=False)
pipe=pipe.to("cuda")
seed=int(hashlib.sha256(str(out).encode()).hexdigest()[:8],16)
g=torch.Generator(device="cuda").manual_seed(seed)
with torch.inference_mode():
 image=pipe(prompt,num_inference_steps=4,guidance_scale=0.0,
            height=512,width=512,generator=g).images[0]
out.parent.mkdir(parents=True,exist_ok=True)
tmp=out.with_suffix(".part.webp")
try:
 image.save(tmp,"WEBP",quality=91,method=5)
 tmp.replace(out)
finally:tmp.unlink(missing_ok=True)
print("COVER40_READY",out,out.stat().st_size)

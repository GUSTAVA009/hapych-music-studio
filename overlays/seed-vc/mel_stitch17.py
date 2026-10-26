"""Stitch predicted log-mels before vocoding to avoid blending unrelated phases.
Vocoder decoding uses deterministic context overlap and exact frame-aligned cropping.
"""
import torch

def accumulate_mel(canvas,weights,part,start,overlap,total):
    part=part.detach().float().cpu();length=min(part.shape[-1],total-start)
    if length<=0:raise ValueError('Empty mel chunk')
    part=part[...,:length]
    w=torch.ones(length,dtype=torch.float32)
    ramp=min(overlap,length)
    if start>0:w[:ramp]=torch.linspace(0.001,1.0,ramp)
    if start+length<total:w[-ramp:]=torch.minimum(w[-ramp:],torch.linspace(1.0,0.001,ramp))
    canvas[...,start:start+length]+=part*w
    weights[start:start+length]+=w

def decode_with_context(mel,vocoder,device,hop=512,body_frames=512,context_frames=172):
    # ~6-second core + 2 seconds of context on both sides at 44.1 kHz.
    if mel.ndim!=3:raise ValueError('Expected [batch,mel,time]')
    total=mel.shape[-1];pieces=[]
    for start in range(0,total,body_frames):
        end=min(total,start+body_frames);left=max(0,start-context_frames);right=min(total,end+context_frames)
        wave=vocoder(mel[...,left:right].to(device).float()).reshape(-1).detach().float().cpu()
        crop=(start-left)*hop;count=(end-start)*hop
        if crop+count>wave.numel():raise RuntimeError('Vocoder output is shorter than its mel timeline')
        pieces.append(wave[crop:crop+count])
    return torch.cat(pieces).unsqueeze(0)

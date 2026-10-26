"""Bounded, locally supervised LoRA training for Seed-VC singing checkpoint.
No production checkpoint is overwritten. Fixed held-out validation selects best.
"""
from pathlib import Path
import os,sys,json,time,random,math,gc,hashlib,copy,traceback
R=Path.home()/'Music Studio';V=R/'Voice Engine'/'seed-vc';os.chdir(V);sys.path.insert(0,str(V))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',PYTHONUTF8='1')
import numpy as np,torch,torchaudio,yaml,requests
from torch import nn
from train_hapych_lowvram import Trainer
from data.ft_dataset import FT_Dataset,collate
D=R/'Training Runs'/'voice23';D.mkdir(parents=True,exist_ok=True)
SEED=230022;MAX_STEPS=200;LR=3e-5;RANK=8
random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED);torch.set_num_threads(4)
P=V/'checkpoints'/'models--Plachta--Seed-VC'/'snapshots'/'257283f9f41585055e8f858fba4fd044e5caed6e'
BASE=P/'DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth'
CFG=D/'voice23_config.yml';cfg=yaml.safe_load((P/'config_dit_mel_seed_uvit_whisper_base_f0_44k.yml').read_text());cfg['log_dir']=str(D/'raw_runs');CFG.write_text(yaml.safe_dump(cfg),encoding='utf-8')
http=requests.Session();http.trust_env=False

def job_active():
 try:
  h=http.get('http://127.0.0.1:7870/api/health',timeout=3).json()
  return h.get('job',{}).get('status') in ('preparing','generating','converting') or h.get('lyrics_busy',False)
 except requests.RequestException:return False

def emit(kind,**kw):
 row={'kind':kind,'time':time.time(),**kw}
 with (D/'metrics.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=True)+'\n')
 print(kind,json.dumps(kw,ensure_ascii=True),flush=True)

class CPUFeaturesTrainer(Trainer):
 def build_sv_model(self,device,config):super().build_sv_model('cpu',config)
 def build_semantic_fn(self,device,config):super().build_semantic_fn('cpu',config)
 def build_f0_fn(self,device,config):super().build_f0_fn('cpu',config)

class LowRankLinear(nn.Module):
 def __init__(self,base):
  super().__init__();self.base=base;self.scale=2.0
  self.A=nn.Parameter(torch.empty(RANK,base.in_features,device=base.weight.device));self.B=nn.Parameter(torch.zeros(base.out_features,RANK,device=base.weight.device));nn.init.kaiming_uniform_(self.A,a=math.sqrt(5))
  for p in base.parameters():p.requires_grad_(False)
 @property
 def weight(self):return self.base.weight
 @property
 def bias(self):return self.base.bias
 def forward(self,x):return self.base(x)+self.scale*torch.nn.functional.linear(torch.nn.functional.linear(x,self.A),self.B)

@torch.no_grad()
def cache_features(trainer,split,augmentations):
 dataset=FT_Dataset(str(D/'dataset'/split),cfg['preprocess_params']['spect_params'],44100,1)
 dataset.data.sort();features=[]
 for index in range(len(dataset)):
  if job_active():raise RuntimeError('A user generation started; training yields the GPU.')
  waves,mels,lengths,mel_lengths=collate([dataset[index]])
  w16=torchaudio.functional.resample(waves,44100,16000)
  Sori=trainer.semantic_fn(w16);f0=trainer.rmvpe.infer_from_audio_batch(w16)
  fb=torchaudio.compliance.kaldi.fbank(w16,num_mel_bins=80,dither=0,sample_frequency=16000);fb=fb-fb.mean(0,keepdim=True)
  style=trainer.sv_fn(fb[None])
  ori=trainer.model.length_regulator(Sori.to('cuda'),ylens=mel_lengths.to('cuda'),f0=f0.to('cuda'))[0].cpu()
  w22=torchaudio.functional.resample(waves,44100,22050);l22=(lengths.float()*22050/44100).long()
  se=trainer.tone_color_converter.extract_se(w22,l22)
  for aug in range(augmentations):
   idx=(index*73+aug*191+(997 if split=='validation' else 0))%len(trainer.se_db)
   converted=trainer.tone_color_converter.convert(w22,l22,se,trainer.se_db[[idx]]).squeeze(1)
   alt16=torchaudio.functional.resample(converted,22050,16000);Salt=trainer.semantic_fn(alt16)
   alt=trainer.model.length_regulator(Salt.to('cuda'),ylens=mel_lengths.to('cuda'),f0=f0.to('cuda'))[0].cpu()
   n=min(mels.shape[-1],ori.shape[1],alt.shape[1]);features.append({'mel':mels[:,:,:n].contiguous(),'ori':ori[:,:n].contiguous(),'alt':alt[:,:n].contiguous(),'style':style.cpu(),'frames':n,'clip':Path(dataset.data[index]).name,'augmentation':aug})
  emit('CACHE',split=split,clip=index+1,total=len(dataset),features=len(features))
 return features

def loss_for(trainer,item):
 n=item['frames'];x=item['mel'].to('cuda');alt=item['alt'].to('cuda');ori=item['ori'].to('cuda');y=item['style'].to('cuda')
 # Prompt and target remain on one continuous timeline. No audio splicing.
 prompt=int(torch.randint(0,max(1,int(n*.55)),(1,)).item());cond=alt.clone();cond[:,:prompt]=ori[:,:prompt]
 with torch.autocast('cuda',dtype=torch.bfloat16):
  loss,_=trainer.model.cfm(x,torch.tensor([n],device='cuda'),torch.tensor([prompt],device='cuda'),cond,y)
 return loss.float()

@torch.no_grad()
def validate(trainer,items):
 trainer.model.cfm.eval();values=[]
 with torch.random.fork_rng(devices=[0]):
  for idx,item in enumerate(items):
   for rep in range(3):
    torch.manual_seed(93000+idx*17+rep);torch.cuda.manual_seed_all(93000+idx*17+rep)
    values.append(float(loss_for(trainer,item)))
 trainer.model.cfm.train()
 return float(np.mean(values))

def adapter_state(modules):return {name:{'A':m.A.detach().cpu().clone(),'B':m.B.detach().cpu().clone(),'scale':m.scale} for name,m in modules.items()}

def main():
 if job_active():raise RuntimeError('User generation active; no training started')
 if (D/'result.json').exists():raise RuntimeError('Completed run exists; do not overwrite evidence')
 started=time.monotonic();emit('START',max_optimizer_steps=MAX_STEPS,base_checkpoint=str(BASE),rank=RANK,learning_rate=LR)
 trainer=CPUFeaturesTrainer(str(CFG),str(BASE),str(D/'dataset'/'train'),'lora23',batch_size=1,num_workers=0,steps=MAX_STEPS,max_epochs=1,device='cuda:0')
 for net in trainer.model.values():
  net.eval()
  for p in net.parameters():p.requires_grad_(False)
 trainer.optimizer=None
 # Verify every parameter before injecting adapters, not merely file existence.
 original=torch.load(BASE,map_location='cpu',weights_only=True)['net'];matched=0
 for component,net in trainer.model.items():
  stored={n.removeprefix('module.'):t for n,t in original[component].items()}
  for name,p in net.named_parameters():
   if name not in stored or p.shape!=stored[name].shape:raise RuntimeError('Parameter mismatch: '+name)
   if not torch.equal(p.detach().cpu(),stored[name]):raise RuntimeError('Parameter was not loaded: '+name)
   matched+=p.numel()
 del original;gc.collect();emit('BASE_VERIFIED',parameter_values=matched)
 cached=D/'feature_cache.pt'
 if cached.exists():features=torch.load(cached,map_location='cpu',weights_only=True)
 else:
  features={'train':cache_features(trainer,'train',3),'validation':cache_features(trainer,'validation',1)};torch.save(features,cached)
 # Frozen feature models stay on CPU and are discarded before optimization.
 for attr in ('whisper_model','whisper_feature_extractor','rmvpe','campplus_model','tone_color_converter','se_db','sv_fn','semantic_fn'):
  if hasattr(trainer,attr):delattr(trainer,attr)
 gc.collect();torch.cuda.empty_cache()
 modules={}
 for name,module in list(trainer.model.cfm.named_modules()):
  if isinstance(module,nn.Linear) and name.endswith(('.attention.wqkv','.attention.wo')):
   parent_name,child=name.rsplit('.',1);parent=trainer.model.cfm.get_submodule(parent_name);wrapper=LowRankLinear(module);setattr(parent,child,wrapper);modules[name]=wrapper
 if not modules:raise RuntimeError('No LoRA layers matched')
 params=[p for m in modules.values() for p in (m.A,m.B)]
 opt=torch.optim.AdamW(params,lr=LR,betas=(.9,.98),weight_decay=.001)
 baseline=validate(trainer,features['validation']);best=baseline;best_step=0;best_state=adapter_state(modules);history=[]
 emit('BASELINE',validation_loss=baseline,trainable_parameters=sum(p.numel() for p in params),adapter_layers=len(modules),train_features=len(features['train']),validation_features=len(features['validation']))
 bad_checks=0;completed=0
 for step in range(1,MAX_STEPS+1):
  if job_active():emit('USER_TASK_PAUSE',step=step-1);break
  trainer.model.cfm.train();item=features['train'][(step-1)%len(features['train'])]
  opt.zero_grad(set_to_none=True);loss=loss_for(trainer,item)
  if not torch.isfinite(loss):raise RuntimeError('Nonfinite training loss')
  loss.backward();grad=torch.nn.utils.clip_grad_norm_(params,1.0,error_if_nonfinite=True);opt.step();completed=step
  lr=LR*(.15+.85*.5*(1+math.cos(math.pi*step/MAX_STEPS)))
  for group in opt.param_groups:group['lr']=lr
  history.append(float(loss.detach()))
  if step%10==0:emit('TRAIN',step=step,mean_loss=float(np.mean(history[-10:])),gradient_norm=float(grad),learning_rate=lr,gpu_peak_mb=round(torch.cuda.max_memory_allocated()/1024**2))
  if step%25==0:
   score=validate(trainer,features['validation']);improved=score<best
   if improved:best=score;best_step=step;best_state=adapter_state(modules);bad_checks=0
   else:bad_checks+=1
   torch.save({'adapters':adapter_state(modules),'step':step,'validation_loss':score,'base':str(BASE)},D/('adapter_step_%04d.pt'%step))
   emit('VALIDATION',step=step,loss=score,best=best,best_step=best_step,improved=improved)
   if bad_checks>=4:emit('EARLY_STOP',reason='four_validation_checks_without_improvement');break
 # Merge only into a NEW checkpoint so normal inference needs no custom loader.
 for name,m in modules.items():
  data=best_state[name];m.A.data.copy_(data['A'].to(m.A.device));m.B.data.copy_(data['B'].to(m.B.device))
 merged={}
 for component,net in trainer.model.items():
  state={k:v.detach().cpu().clone() for k,v in net.state_dict().items()}
  if component=='cfm':
   for name,m in modules.items():
    weight=state.pop(name+'.base.weight');state.pop(name+'.A');state.pop(name+'.B')
    if name+'.base.bias' in state:state[name+'.bias']=state.pop(name+'.base.bias')
    state[name+'.weight']=weight+best_state[name]['scale']*(best_state[name]['B']@best_state[name]['A'])
  merged[component]=state
 weight_delta_sq=sum(float(((s['B']@s['A'])*s['scale']).square().sum()) for s in best_state.values())
 candidate=D/'best_model.pth';torch.save({'net':merged},candidate)
 torch.save({'adapters':best_state,'best_step':best_step,'base':str(BASE),'rank':RANK},D/'best_adapter.pt')
 manifest=json.loads((D/'dataset_manifest.json').read_text(encoding='utf-8'))
 result={'status':'completed','optimizer_steps':completed,'max_requested_steps':MAX_STEPS,'best_step':best_step,'validation_before':baseline,'validation_best':best,'relative_validation_reduction':(baseline-best)/baseline,'updated_adapter_parameters':sum(p.numel() for p in params),'merged_weight_delta_l2':math.sqrt(weight_delta_sq),'candidate':str(candidate),'config':str(CFG),'seconds':round(time.monotonic()-started,2),'train_seconds':manifest['train_seconds'],'validation_seconds':manifest['validation_seconds'],'train_audio_sources':2,'validation_audio_sources':1,'deployed':False,'perceptual_quality_verified':False,'music_generator_weights_trained':False,'base_checkpoint_unchanged':True}
 (D/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');emit('COMPLETE',**result)

if __name__=='__main__':
 try:main()
 except BaseException as exc:
  emit('FAILED',error=str(exc));traceback.print_exc();raise

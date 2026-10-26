"""CPU inference bridge for the actually trained groove23 weights; no network.
Outputs learned kick/snare/hat events, with no hidden fixed drum template.
"""
from pathlib import Path
import json,hashlib,re,sys,argparse
ROOT=Path.home()/'Music Studio';MODEL_DIR=ROOT/'Training Runs'/'groove23'
def infer(style,bpm,seed,bars=8):
 import torch
 sys.path.insert(0,str(MODEL_DIR))
 from groove_model23 import GrooveModel
 checkpoint=MODEL_DIR/'best_groove_model.pt'
 state=torch.load(checkpoint,map_location='cpu',weights_only=True)
 styles=state['styles'];text=str(style).lower()
 genre='dance' if re.search(r'house|dance|edm|клуб|танцев',text) else 'hiphop' if re.search(r'808|rap|hip.?hop|trap|drill|рэп|трэп|дрилл',text) else 'pop'
 if genre not in styles:raise ValueError('Trained rhythm style unavailable')
 if not 30<=float(bpm)<=300 or not 2<=bars<=32 or bars%2:raise ValueError('Invalid rhythm dimensions')
 torch.set_num_threads(2)
 model=GrooveModel(max(styles.values())+1,state['hidden']);model.load_state_dict(state['state_dict'],strict=True);model.eval()
 generator=torch.Generator(device='cpu');generator.manual_seed(int(seed))
 events=[];patterns=[];retries=0
 with torch.inference_mode():
  for segment in range(bars//2):
   accepted=None
   for attempt in range(8):
    tokens=torch.full((1,1),512,dtype=torch.long);part=[];pattern=[]
    for step in range(32):
     logits,velocity,offset=model(tokens,torch.tensor([styles[genre]]),torch.tensor([float(bpm)]),torch.tensor([int(segment==bars//2-1 and attempt%2==1)]))
     # Model originally has 9 drum roles. Keep supported electronic-kit roles;
     # never map ride/toms to hats, which would create dense noisy patterns.
     scores=logits[0,-1,:16]/.88
     mask=int(torch.multinomial(torch.softmax(scores,-1),1,generator=generator));pattern.append(mask)
     for role in range(4):
      if mask&(1<<role):
       timing=max(-.08,min(.08,float(offset[0,-1,role])/4))
       beat=max(segment*8,min(segment*8+7.999,segment*8+step/4+timing))
       vel=max(25,min(120,round(float(velocity[0,-1,role])*127)))
       part.append({'beat':round(beat,6),'role':role,'velocity':vel,'grid_step':segment*32+step})
     tokens=torch.cat((tokens,torch.tensor([[mask]])),1)
    counts=[sum(e['role']==r for e in part) for r in range(4)]
    if 2<=counts[0]<=12 and 2<=counts[1]<=12 and 4<=counts[2]+counts[3]<=28:
     accepted=(part,pattern);break
    retries+=1
   if accepted is None:raise RuntimeError('Learned rhythm failed density checks; no fixed pattern substituted')
   events.extend(accepted[0]);patterns.append(accepted[1])
 return {'events':sorted(events,key=lambda e:(e['beat'],e['role'])),'patterns':patterns,'style':genre,'bpm':float(bpm),'bars':bars,'seed':int(seed),'model_step':state['step'],'model_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'learned_weights_used':True,'constrained_roles':[0,1,2,3],'rejected_candidates':retries,'training_attribution':'Groove MIDI Dataset, Google/Magenta, CC BY 4.0; see Training Runs/groove23/source.json','perceptual_quality_verified':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--output',required=True);a=p.parse_args();req=json.loads(Path(a.request).read_text(encoding='utf-8'));result=infer(req['style'],req['bpm'],req['seed'],req.get('bars',8));Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('LEARNED_RHYTHM_OK',len(result['events']),flush=True)

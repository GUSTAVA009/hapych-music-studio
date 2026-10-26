import torch
print('CUDA',torch.cuda.is_available())
x=torch.ones((32,32),device='cuda')
print('CUDA_MATMUL',float((x@x).mean()),'GPU_MB',round(torch.cuda.memory_allocated()/1048576,2))
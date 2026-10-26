@echo off
setlocal
cd /d "%~dp0ACE-Step-1.5"
set "NO_PROXY=127.0.0.1,localhost,::1"
set "no_proxy=127.0.0.1,localhost,::1"
set "PYTHONUTF8=1"
set "CHECK_UPDATE=false"
set "CUDA_VISIBLE_DEVICES=0"
".venv\Scripts\acestep.exe" --port 7860 --server-name 127.0.0.1 --language en --config_path acestep-v15-turbo --lm_model_path acestep-5Hz-lm-0.6B --backend pt --init_service true --init_llm true --offload_to_cpu true --offload_dit_to_cpu true --quantization none --batch_size 1

@echo off
setlocal
cd /d "%~dp0ACE-Step-1.5"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
set "CHECK_UPDATE=false"
set "PORT=7860"
set "SERVER_NAME=127.0.0.1"
set "NO_PROXY=127.0.0.1,localhost,::1"
set "no_proxy=127.0.0.1,localhost,::1"
set "CONFIG_PATH=--config_path acestep-v15-turbo"
set "LM_MODEL_PATH=--lm_model_path acestep-5Hz-lm-0.6B"
set "OFFLOAD_TO_CPU=--offload_to_cpu true"
set "INIT_LLM=--init_llm true"
call start_gradio_ui.bat

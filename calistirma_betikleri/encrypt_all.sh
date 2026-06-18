#!/bin/bash
mkdir -p /home/ardam/underw_framework/encrypted_models
cd /home/ardam/underw_framework/CyberPUF_LLM

echo 'Starting DeepSeek...'
/home/ardam/underw_framework/ai_env/bin/python llm_encryptor.py /home/ardam/.cache/huggingface/hub/models--OpenVINO--DeepSeek-R1-Distill-Qwen-7B-nf4-ov/snapshots/e35ea4e9f66c4c6accbcf8b0450454ab6fb34653 /home/ardam/underw_framework/encrypted_models/DeepSeek-R1-Distill-Qwen-7B-nf4-ov.cpuf_llm

echo 'Starting Mistral...'
/home/ardam/underw_framework/ai_env/bin/python llm_encryptor.py /home/ardam/.cache/huggingface/hub/models--OpenVINO--Mistral-7B-Instruct-v0.3-int4-ov/snapshots/48ff2bf3fe0134f1a518afe0023926c8a09565f5 /home/ardam/underw_framework/encrypted_models/Mistral-7B-Instruct-v0.3-int4-ov.cpuf_llm

echo 'Starting Qwen2.5-1.5B...'
/home/ardam/underw_framework/ai_env/bin/python llm_encryptor.py /home/ardam/.cache/huggingface/hub/models--OpenVINO--Qwen2.5-1.5B-Instruct-int4-ov/snapshots/4d14c299e35d8b74e3471f9e92bd1377fae50736 /home/ardam/underw_framework/encrypted_models/Qwen2.5-1.5B-Instruct-int4-ov.cpuf_llm

echo 'Starting Qwen2.5-7B...'
/home/ardam/underw_framework/ai_env/bin/python llm_encryptor.py /home/ardam/.cache/huggingface/hub/models--OpenVINO--Qwen2.5-7B-Instruct-int4-ov/snapshots/51f38f02586876c08ca2a604224da20ea61685b8 /home/ardam/underw_framework/encrypted_models/Qwen2.5-7B-Instruct-int4-ov.cpuf_llm

echo 'Starting Qwen2.5-14B...'
/home/ardam/underw_framework/ai_env/bin/python llm_encryptor.py /home/ardam/.cache/huggingface/hub/models--OpenVINO--Qwen2.5-14B-Instruct-int4-ov/snapshots/67c99648107c454a46b60078fb591bd5ecb2ded1 /home/ardam/underw_framework/encrypted_models/Qwen2.5-14B-Instruct-int4-ov.cpuf_llm

echo 'Done.'

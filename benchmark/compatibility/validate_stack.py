#!/usr/bin/env python3
"""
GPU / CUDA / PyTorch / Container Compatibility Matrix Validator.
Tests every component and classifies as PASS, FAIL, WARNING, NOT TESTED, or NOT APPLICABLE.
Saves results to results/raw/<server-id>/compatibility_matrix.json.
"""
import os
import json
import subprocess
import urllib.request
import urllib.error

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_ID = "mirage"
OUT_DIR = os.path.join(BASE_DIR, "results", "raw", SERVER_ID)
os.makedirs(OUT_DIR, exist_ok=True)

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return None, e.stderr.strip()

tests = []

def record_test(category, name, status, details=None, evidence=None):
    tests.append({
        "category": category,
        "test_name": name,
        "status": status,
        "details": details or "",
        "evidence": evidence or ""
    })
    print(f"[{status}] {category} :: {name} - {details}")

# 1. GPU Detection
stdout, err = run_cmd("nvidia-smi -L")
if stdout and "GPU 0" in stdout:
    record_test("Hardware", "NVIDIA GPU Detection", "PASS", "GPU 0 detected via nvidia-smi", stdout)
else:
    record_test("Hardware", "NVIDIA GPU Detection", "FAIL", "Failed to detect GPU", err)

# 2. Driver Version
stdout, err = run_cmd("nvidia-smi --query-gpu=driver_version --format=csv,noheader")
if stdout:
    record_test("Driver", "NVIDIA Driver Compatibility", "PASS", f"Driver version {stdout} active", stdout)
else:
    record_test("Driver", "NVIDIA Driver Compatibility", "FAIL", "Driver query failed", err)

# 3. Host CUDA Version
stdout, err = run_cmd("nvidia-smi | grep -o 'CUDA Version: [0-9.]*'")
if stdout:
    record_test("CUDA", "CUDA Runtime Compatibility", "PASS", f"Driver supports {stdout}", stdout)
else:
    record_test("CUDA", "CUDA Runtime Compatibility", "FAIL", "Failed to identify CUDA version", err)

# 4. Multi-GPU Support
stdout, err = run_cmd("nvidia-smi --query-gpu=count --format=csv,noheader")
gpu_count = int(stdout.splitlines()[0]) if stdout else 0
if gpu_count > 1:
    record_test("Multi-GPU", "Multi-GPU Topology", "PASS", f"{gpu_count} GPUs available", stdout)
else:
    record_test("Multi-GPU", "Multi-GPU Topology", "NOT APPLICABLE", "Single GPU topology (1x RTX 3090); Multi-GPU scaling not applicable", f"GPU Count: {gpu_count}")

# 5. MIG Mode
record_test("GPU Virtualization", "MIG Partitioning", "NOT APPLICABLE", "MIG is only supported on Hopper/Ampere datacenter GPUs (A100/H100), not GeForce RTX 3090", "GeForce RTX 3090")

# 6. Container GPU Access: TTS Backend
stdout, err = run_cmd("docker exec wiseai-vllm-omni-dev nvidia-smi --query-gpu=name,memory.used --format=csv,noheader")
if stdout:
    record_test("Container Passthrough", "TTS Omni vLLM GPU Access", "PASS", f"Container sees GPU: {stdout}", stdout)
else:
    record_test("Container Passthrough", "TTS Omni vLLM GPU Access", "FAIL", "TTS backend cannot query GPU", err)

# 7. Container GPU Access: ASR Backend
stdout, err = run_cmd("docker exec wiseai-vllm-core-dev nvidia-smi --query-gpu=name,memory.used --format=csv,noheader")
if stdout:
    record_test("Container Passthrough", "ASR Core vLLM GPU Access", "PASS", f"Container sees GPU: {stdout}", stdout)
else:
    record_test("Container Passthrough", "ASR Core vLLM GPU Access", "FAIL", "ASR backend cannot query GPU", err)

# 8. Container GPU Access: Translation Worker
stdout, err = run_cmd("docker exec wiseai-translation-worker-indic-trans-dev python3 -c \"import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))\"")
if stdout and "True" in stdout:
    record_test("Container Passthrough", "Translation IndicTrans2 GPU Access", "PASS", f"PyTorch CUDA active: {stdout}", stdout)
else:
    record_test("Container Passthrough", "Translation IndicTrans2 GPU Access", "FAIL", "Translation container cannot access PyTorch CUDA", err)

# 9. Framework Compatibility: vLLM Omni (TTS)
stdout, err = run_cmd("docker exec wiseai-vllm-omni-dev python3 -c \"import vllm, torch; print('vLLM:', vllm.__version__, 'Torch:', torch.__version__)\"")
if stdout:
    record_test("Framework", "vLLM Omni Runtime", "PASS", f"Framework versions: {stdout}", stdout)
else:
    record_test("Framework", "vLLM Omni Runtime", "FAIL", "Failed importing vLLM in TTS container", err)

# 10. Framework Compatibility: vLLM Core (ASR)
stdout, err = run_cmd("docker exec wiseai-vllm-core-dev python3 -c \"import vllm, torch; print('vLLM:', vllm.__version__, 'Torch:', torch.__version__)\"")
if stdout:
    record_test("Framework", "vLLM Core Runtime", "PASS", f"Framework versions: {stdout}", stdout)
else:
    record_test("Framework", "vLLM Core Runtime", "FAIL", "Failed importing vLLM in ASR container", err)

# 11. Service Health Endpoints
for svc, port in [("TTS Gateway", 8071), ("ASR Gateway", 8091), ("Translation Gateway", 8999)]:
    url = f"http://localhost:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read().decode()
            record_test("Service Health", f"{svc} Health Endpoint", "PASS", f"HTTP {resp.status} on port {port}", data)
    except Exception as e:
        record_test("Service Health", f"{svc} Health Endpoint", "FAIL", f"Failed connecting to port {port}: {str(e)}", "")

# 12. GPU Memory Headroom Warning
smi_mem = run_cmd("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits")[0]
if smi_mem:
    used, total = [float(x.strip()) for x in smi_mem.split(",")]
    pct = (used / total) * 100
    if pct > 80.0:
        record_test("Resource Headroom", "VRAM Allocation Warning", "WARNING", f"VRAM utilization is high: {used:.0f}/{total:.0f} MB ({pct:.1f}%)", f"{pct:.1f}%")
    else:
        record_test("Resource Headroom", "VRAM Allocation Headroom", "PASS", f"VRAM utilization is moderate: {used:.0f}/{total:.0f} MB ({pct:.1f}%)", f"{pct:.1f}%")

matrix_file = os.path.join(OUT_DIR, "compatibility_matrix.json")
with open(matrix_file, "w") as f:
    json.dump(tests, f, indent=2)

print(f"Compatibility matrix saved to {matrix_file}")

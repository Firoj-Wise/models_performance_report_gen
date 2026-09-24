# DevOps Q&A: GPU Platform Validation & WiseAI Benchmarking

This document outlines auto-discovered deployment parameters and captures questions requiring confirmation from the DevOps engineering team prior to running load, concurrency, scalability, and stress benchmarking.

---

## 1. Summary of Discovery Status

| Status Category | Description | Count |
|---|---|---|
| **Confirmed from Server** | Automatically discovered from host OS, hardware, Docker runtime, container inspection, and live service probes. | 18 |
| **Requires DevOps Confirmation** | Critical deployment, boundary, safety, or baseline parameters that cannot be inferred without human confirmation. | 14 |
| **Not Applicable** | Configuration options ruled out by physical topology or current deployment architecture. | 2 |

---

## 2. DevOps Questionnaire Table

| Category | Question | Auto-discovered Information | DevOps Confirmation | Benchmark Impact |
|---|---|---|---|---|
| **Environment / Safety** | Is server `mirage` considered Development, Staging, Dedicated Benchmark, or Production? | Hostname: `mirage`. Container names and tags use `-dev` suffix (e.g., `wiseai-tts-api-dev`, `wiseai-asr-api-dev`). Other team services (Asterisk, Temporal, Solr, Portainer, Chat Widget) are running simultaneously. | `[REQUIRES CONFIRMATION]` | Determines whether high concurrency, sustained load, and stress testing are permitted without risking service disruption for other engineers. |
| **Environment / Safety** | Are concurrency testing and sustained load testing permitted on this server? | Server currently handles active dev/staging workloads with 16 GB / 24.5 GB VRAM utilized. | `[REQUIRES CONFIRMATION]` | Safety boundary: Prevents running test matrices that could exhaust resources or crash co-hosted services. |
| **Environment / Safety** | What is the maximum safe concurrency limit for this server? | Current vLLM / worker configs: ASR vLLM `batch_size: 8`, TTS CUDA graph batch sizes `1,2,3,4`, Translation worker single process. | `[REQUIRES CONFIRMATION]` | Defines upper bounds for concurrency ramps (e.g., stopping at 4, 8, 16, or 32). |
| **Environment / Safety** | Are there specific maintenance windows or timeframes when benchmarking should be executed? | Current local time is business hours; multi-user processes exist on machine. | `[REQUIRES CONFIRMATION]` | Scheduling benchmarks to avoid interference with active development or call tests. |
| **Docker** | Are the currently running containers and `:latest` images the official baseline images for the June/July validation reports? | Running: <br>• TTS API: `registry.wiseai.wiseyak.com/wiseai-tts-api-dev:latest`<br>• TTS Backend: `registry.wiseai.wiseyak.com/wiseyak-vllm-omni:latest`<br>• ASR API: `registry.wiseai.wiseyak.com/wiseai-asr-api-dev:latest`<br>• ASR Backend: `registry.wiseai.wiseyak.com/wiseai-vllm-asr:latest`<br>• Translation API: `registry.wiseai.wiseyak.com/wiseai-translation-api-dev:latest`<br>• Translation Worker: `registry.wiseai.wiseyak.com/wiseai-translation-worker-indic-trans-dev:latest` | `[REQUIRES CONFIRMATION]` | Ensures validation reports reference the intended baseline release rather than transient development builds. |
| **Docker** | Are there specific image digest tags (immutable tags) that should be recorded instead of `:latest`? | Image IDs auto-discovered:<br>• TTS API: `05dc563ca18f`<br>• TTS Omni: `51717a567838`<br>• ASR API: `a5c2bc762575`<br>• ASR vLLM: `455c00cda547`<br>• Translation API: `e1327f9d...`<br>• Translation Worker: `7d722943...` | `[REQUIRES CONFIRMATION]` | Guarantees auditability and reproducibility across runs. |
| **Docker** | Should non-WiseAI auxiliary services (e.g. `hungry_ramanujan` text-embeddings-inference, `wiseai-svc-fastapi-dev`, Asterisk) remain running during the benchmark? | Auxiliary containers currently occupy ~1.2 GB VRAM (`text-embeddings-router`: 882 MiB, python processes: ~300 MiB). | `[REQUIRES CONFIRMATION]` | Establishes whether benchmark measurements reflect shared-server reality or isolated peak performance. |
| **GPU & Allocation** | Is sharing GPU 0 (`NVIDIA GeForce RTX 3090`, 24 GB) across all three services (TTS, ASR, Translation) the intended standard deployment? | Single GPU present (`0000:01:00.0`). All 3 services are sharing this single GPU alongside auxiliary processes. VRAM footprint: 16.15 GB / 24.57 GB. | `[REQUIRES CONFIRMATION]` | Identifies whether cross-service resource contention is an intended operational condition to benchmark or an artifact of the dev environment. |
| **GPU & Allocation** | Should single-GPU isolated benchmarks be performed (evaluating one service at a time with others idle), or full concurrent multi-service load? | Currently all 3 services are active and reachable. | `[REQUIRES CONFIRMATION]` | Dictates benchmark execution strategy: isolated service saturation vs composite system load. |
| **GPU & Topology** | Are Multi-GPU or MIG partitioning configurations relevant for this server? | Host has 1x RTX 3090 (Consumer Ampere architecture; MIG is not supported on GeForce hardware; single GPU topology). | **NOT APPLICABLE** (Physical hardware limitation: 1 GPU, No MIG) | Multi-GPU scaling and MIG tests are marked N/A for this server. |
| **Models & Precision** | Are the discovered model checkpoints and precisions the official benchmark configurations?<br>• TTS: `omnivoice_nepali_tts` (repo: `mlwiseyak/omnivoice-nepali-tts-v2`, 16 steps)<br>• ASR: `bodhan-ai/indic-transcribe-core` (bfloat16, vLLM max-model-len 448)<br>• Translation: `indictrans2-indic-en-dist-200M` & `indictrans2-en-indic-dist-200M` (PyTorch CUDA FP16/FP32) | Discovered from container commands, environment variables, and `/info` endpoints. | `[REQUIRES CONFIRMATION]` | Precision and architecture directly dictate compute/memory throughput and latency bounds. |
| **Service Endpoints** | Are standard HTTP REST endpoints the primary benchmark interface?<br>• TTS: `POST /generate_from_text`<br>• ASR: `POST /transcribe-from-stream`<br>• Translation: `POST /translate` and `/raw-translate` | Endpoints probed and confirmed responding with health status `healthy`. ZMQ brokers are internal (ports 5555-5560). | `[REQUIRES CONFIRMATION]` | Focuses benchmark harness on client-facing ingress latency. |
| **Monitoring** | Should the benchmark framework tap into the existing Prometheus exporters (`nvidia_gpu_exporter` on port 9835, `node-exporter` on port 9100) or run dedicated background sampling via `nvidia-smi`? | Exporters auto-discovered and active on `localhost:9835` and `localhost:9100`. | `[REQUIRES CONFIRMATION]` | Reuses existing production-grade telemetry to minimize benchmark overhead. |
| **Performance Targets** | Are there existing SLA or target performance thresholds for WiseAI services? (e.g. Real-Time Factor < 0.3 for ASR/TTS, P95 latency < 500ms, Target RPS)? | None configured in code/compose files. | `[REQUIRES CONFIRMATION]` | Provides objective pass/fail criteria for the June/July validation reports. |
| **Metrics Priority** | Which metrics represent top business priority for the engineering team?<br>(Latency P50/P95/P99 vs Throughput RPS vs Real-Time Factor vs VRAM headroom vs Power/Thermal) | Metrics collector supports all standard dimensional metrics. | `[REQUIRES CONFIRMATION]` | Focuses executive summary and scaling conclusions on organizational goals. |

---

## 3. Discovered Configuration Snapshot (Read-Only)

### Hardware & Operating System
- **Host**: `mirage`
- **OS**: Ubuntu 22.04.5 LTS (Jammy Jellyfish), Kernel `6.8.0-1059-nvidia`
- **CPU**: AMD Ryzen 9 7950X 16-Core Processor (32 threads, 1 socket, 1 NUMA node)
- **RAM**: 62 GiB total (16 GiB used, 44 GiB available, 85 GiB Swap)
- **Disk**: NVMe `/dev/nvme0n1p2`, 529 GB total (207 GB used, 296 GB available / 42%)
- **GPU 0**: NVIDIA GeForce RTX 3090, 24,576 MiB VRAM (Driver: `595.84`, CUDA Version: `13.2`, Compute Capability `8.6`)
- **GPU Memory State**: 16,151 MiB currently allocated across active engines.

### Services Mapping
1. **WiseAI TTS**:
   - **Gateway**: `wiseai-tts-api-dev` on port `8071`
   - **Backend**: `wiseai-vllm-omni-dev` on port `8092`
   - **Engine**: `omnivoice_tts` (`mlwiseyak/omnivoice-nepali-tts-v2`) via vLLM Omni v0.28.0 (Torch 2.13.0+cu130)
   - **Default Speaker**: `Prakash_0`
2. **WiseAI ASR**:
   - **Gateway**: `wiseai-asr-api-dev` on port `8091`
   - **Backend**: `wiseai-vllm-core-dev` on port `8399`
   - **Engine**: `indic-transcribe-core` (`bodhan-ai/indic-transcribe-core`) via vLLM v0.26.1rc1 (Torch 2.13.0+cu132, bfloat16)
3. **WiseAI Translation**:
   - **Gateway**: `wiseai-translation-api-dev` on port `8999`
   - **Worker**: `wiseai-translation-worker-indic-trans-dev` on port `51001`
   - **Engine**: IndicTrans2 (`mlwiseyak/nep-eng-indictrans2-v3-address-6400` & `eng-nep-indictrans2-v1-address-8600`)

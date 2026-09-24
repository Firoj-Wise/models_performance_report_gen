# Agent Instructions & Operating Manual: WiseAI GPU Performance & Scalability Framework

This document serves as the mandatory operational protocol and technical guideline for AI coding agents working in this repository.

---

## 1. Absolute Core Mandate: 100% REAL & MEASURED DATA

> [!IMPORTANT]
> **ZERO INTERPOLATION / ZERO FABRICATION / ZERO PLACEHOLDERS / ZERO HARDCODING**
> 1. All performance metrics (Throughput RPS, Latency P50/P95/Mean, Real-Time Factor, GPU Core %, VRAM MiB) must originate from **actual physical test execution and live NVML / HTTP telemetry**.
> 2. Hardware characteristics (CPU model, RAM, GPU model, driver, CUDA runtime, VRAM) and Docker configurations (container names, image digests, port bindings, runtime commands) must be discovered dynamically via `system_info.py` or loaded directly from `config/manifest.yaml`.
> 3. No code or report generator may hardcode synthetic metrics. When generating reports, scripts must dynamically parse `results/raw/<server_id>/` and `results/processed/<server_id>/summary.json`.

---

## 2. Repository Architecture & Workflow Stages

The framework is organized into 5 modular, automated phases:

```text
models_performance_report_gen/
│
├── benchmark/
│   ├── discovery/         # Hardware, OS, and Docker container inspection
│   │   ├── system_info.py # Probes pynvml, sysfs, and Docker socket
│   │   └── inspect_images.py # Deeply inspects Docker image layers, env vars, and runtimes
│   ├── compatibility/     # Pre-flight smoke testing and GPU passthrough audits
│   │   ├── validate_stack.py # Validates service health and functional endpoints
│   │   └── validate_optimizations.py # Profiles dynamic batching, warmup, and VRAM headroom
│   ├── benchmarks/        # Master multi-service test runner
│   │   └── run_suite.py
│   ├── load/              # Concurrency testing engine with warmup isolation
│   │   └── runner.py
│   ├── monitoring/        # Real-time 100ms background NVML telemetry daemon
│   │   ├── collector.py   # High-frequency NVML telemetry poller
│   │   └── audit_logs.py  # Structured log and request lifecycle auditor
│   └── analysis/          # Dynamic SVG/PNG chart plotting and MD/DOCX report compilers
│       ├── plot_charts.py
│       ├── plot_png_charts.py
│       ├── generate_reports.py
│       └── generate_docx_reports.py
│
├── config/
│   └── manifest.yaml      # Machine-readable server & container manifest
│
├── data/
│   ├── audio/             # Standardized audio corpuses (audio_medium.wav)
│   └── text/              # Standardized Nepali / English text payloads
│
├── docs/
│   ├── devops_questions.md        # DevOps Q&A, boundaries, and discovered config
│   └── methodology_and_metrics.md # Detailed metrics formulas and pipeline guide
│
├── results/
│   ├── raw/<server_id>/        # Raw request CSVs, system_info.json, compatibility_matrix.json
│   ├── processed/<server_id>/  # summary.json with computed latency/throughput/RTF aggregations
│   └── charts/<server_id>/     # Generated SVG and PNG visualization charts
│
├── reports/
│   ├── june/              # June Platform Validation Report (.md & .docx)
│   ├── july/              # July Performance & Scalability Report (.md & .docx)
│   └── august/            # August Monitoring, Logging & Optimization Report (.md & .docx)
│
└── scripts/               # Single-command reproduction shell scripts
    ├── discover.sh        # Runs Stage 1: Discovery
    ├── validate.sh        # Runs Stage 2: Compatibility & Smoke Validation
    ├── benchmark.sh       # Runs load test for single service
    ├── benchmark_all.sh   # Runs full multi-service matrix across C=1, 2, 4, 8
    └── generate_report.sh # Compiles all charts, MD, and DOCX reports
```

---

## 3. How Agents Must Execute the Pipeline

When an agent needs to execute or verify benchmarks on the target server, follow this strict execution sequence:

### Step 1: System & Container Discovery
```bash
./scripts/discover.sh
```
* **Script Action**: Executes `benchmark/discovery/system_info.py`.
* **Output Generated**: `results/raw/<server_id>/system_info.json`.
* **Verification**: Verify that GPU 0 (`NVIDIA GeForce RTX 3090`), driver version (`595.84`), CUDA version (`13.2`), and active containers are recorded accurately.

### Step 2: Compatibility & Functional Validation
```bash
./scripts/validate.sh
```
* **Script Action**: Executes `benchmark/compatibility/validate_stack.py`.
* **Output Generated**: `results/raw/<server_id>/compatibility_matrix.json`.
* **Checks**:
  - Validates NVIDIA GPU runtime passthrough in each container.
  - Checks HTTP `/health` endpoints on gateway ports (`8071`, `8091`, `8999`).
  - Sends live functional test payloads to `/generate_from_text`, `/transcribe-from-stream`, and `/translate`.

### Step 3: Concurrency & Scalability Load Benchmarks
```bash
./scripts/benchmark_all.sh
```
* **Script Action**: Executes `benchmark/benchmarks/run_suite.py`.
* **Protocol**:
  - Sweeps Concurrency tiers: **1, 2, 4, and 8**.
  - Runs **2 warmup requests** per tier to pre-fill KV-cache and capture CUDA execution graphs. Warmup metrics are strictly purged from calculations.
  - Executes **8 measured steady-state requests** per tier.
  - Concurrently spawns the **100ms NVML telemetry daemon** (`benchmark/monitoring/collector.py`) to capture GPU Compute %, VRAM MiB, Power W, and Board Temperature.
* **Output Generated**: Raw per-request latency logs and `results/processed/<server_id>/summary.json`.

### Step 4: Re-generate Visual Charts & Formal Deliverables
```bash
./scripts/generate_report.sh
```
* **Script Action**:
  1. `plot_charts.py` $\rightarrow$ Generates vector SVGs in `results/charts/<server_id>/`.
  2. `plot_png_charts.py` $\rightarrow$ Generates high-resolution PNGs in `results/charts/<server_id>/`.
  3. `generate_reports.py` $\rightarrow$ Compiles formal Markdown reports in `reports/june/`, `reports/july/`, and `reports/august/`.
  4. `generate_docx_reports.py` $\rightarrow$ Compiles executive Word documents (`.docx`) in `reports/` and copies them to the workspace root.

---

## 4. Docker Architecture & Container Image Evaluation

When evaluating the container environment for the **August Monitoring, Logging, and Optimization Framework**, agents must understand the dual-tier container topology:

```
[ CLIENT TRAFFIC ]
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ INGRESS GATEWAYS (FastAPI / CPU Only)                                           │
│  • wiseai-tts-api-dev (Port 8071)         • wiseai-asr-api-dev (Port 8091)      │
│  • wiseai-translation-api-dev (Port 8999)                                       │
│  Role: HTTP ingress parsing, connection management, request tracing, async IPC  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Internal Bridge / ZeroMQ / Localhost IPC
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ BACKEND INFERENCE ENGINES (GPU Accelerated via NVIDIA Container Toolkit)        │
│  • wiseai-vllm-omni-dev (Port 8092)  ──> Flow-matching TTS (16 steps, CUDA graphs)│
│  • wiseai-vllm-core-dev (Port 8399)  ──> Canary ASR (bfloat16 continuous batch) │
│  • wiseai-translation-worker (Port 51001) ──> IndicTrans2 PyTorch CUDA worker   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Docker Evaluation Rules
1. **Container Passthrough**: Confirm GPU device access via `--gpus all` or Docker compose `device_ids: ['0']`.
2. **Image Inspection**: Verify that images use optimized runtime wheels (e.g. `vLLM 0.28.0` with `Torch 2.13.0+cu130`, `vLLM 0.26.1rc1` with `Torch 2.13.0+cu132`).
3. **Memory Isolation**: Ensure memory allocations are bounded (`gpu_memory_utilization: 0.30` for ASR, 5.6 GB for TTS, 1.1 GB for Translation) to prevent Out-Of-Memory collisions on the shared 24 GB card.

---

## 5. Scope of the Three Milestone Deliverables

Agents modifying or referencing reports must preserve their specific designated scopes:

| Month Deliverable | Document Title | Primary Focus |
|---|---|---|
| **June Report** | **GPU platform validation and compatibility testing report** | Pre-flight platform readiness, NVIDIA driver, CUDA 13.2 support, Docker passthrough, smoke test matrix. |
| **July Report** | **Performance benchmarking and scalability analysis report** | Empirical load testing, Concurrency ramps (1 to 8), Overall Latency, Throughput (req/s), Real-Time Factor (RTF), GPU Compute %. |
| **August Report** | **Monitoring, logging, and performance optimization framework** | Docker container architecture, 100ms NVML telemetry, structured request logging, vLLM continuous batching, CUDA graphs, flow-matching step tuning, VRAM co-existence. |

---

## 6. Code Extension Guidelines

If adding new benchmark features or modifying existing pipelines:
* **Preserve Dynamic Loading**: Always load server attributes and metrics from `config/manifest.yaml` and `results/processed/<server_id>/summary.json`.
* **Never Hardcode Target Server Values**: Use `SERVER_ID` dynamically so the framework can run on any server (`mirage`, `nebula`, `titan`, etc.).
* **Retain Warmup Isolation**: Ensure any new load generator explicitly discards warmup cycles from final statistical aggregations.

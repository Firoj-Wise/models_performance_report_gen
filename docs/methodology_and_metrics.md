# WiseAI Benchmarking Methodology & Metrics Guide

This document explains **how the platform benchmarking was conducted**, the architectural pipeline behind the test suite, and **what each measured metric means** for production capacity planning.

---

## 1. How We Did It: Architectural & Execution Pipeline

The benchmarking suite is engineered as a reproducible, automated testing framework divided into five modular stages:

```
+-----------------------------------------------------------------------------------+
|                            Benchmarking Pipeline                                  |
+-----------------------------------------------------------------------------------+
|  1. Discovery     --> Probes physical CPU/GPU topology, CUDA runtime & Docker     |
|  2. Validation    --> Pre-flight smoke tests & container passthrough checks       |
|  3. Load Testing  --> Multi-threaded client requests (C=1, 2, 4, 8) with Warmup   |
|  4. Telemetry     --> Real-time 100ms background sampling of GPU Compute & VRAM   |
|  5. Reporting     --> Programmatic SVG/PNG charts and formal Markdown / DOCX docs |
+-----------------------------------------------------------------------------------+
```

### Stage 1: Hardware & Container Environment Discovery
* **Tooling**: Direct inspection via NVIDIA Management Library (`pynvml`), Linux sysfs (`/sys/devices/system/cpu`), and the Docker Engine API socket (`/var/run/docker.sock`).
* **Purpose**: Capture the exact physical baseline (e.g. NVIDIA GeForce RTX 3090 24GB, AMD Ryzen 9 5950X 16-Core, Docker 29.6.1) without manual transcription.
* **Output**: `results/raw/<server_id>/system_info.json`.

### Stage 2: Pre-Flight Platform & Compatibility Validation
* **Execution**: Before any load test, the framework executes functional smoke tests against all microservice endpoints:
  - **WiseAI Translation**: `POST /translate` (IndicTrans2)
  - **WiseAI ASR**: `POST /transcribe-from-stream` (IndicTranscribe vLLM Core)
  - **WiseAI TTS**: `POST /generate_from_text` (OmniVoice vLLM Omni)
* **Checks**: Confirms that model weights are loaded into VRAM, GPU IOCTL bindings are functioning, and ZeroMQ queues are communicating.

### Stage 3: Controlled Concurrency Load Generation
* **Isolation of Cold Starts**: 
  - The first 1–2 requests to an AI model trigger CUDA kernel compilation, memory paging, and vLLM KV-cache graph capture. These cold-start anomalies produce artificially inflated latency.
  - The test harness runs an explicit **warmup phase** (2 sequential requests) to prime the models. Warmup metrics are **strictly discarded** from all statistical evaluations.
* **Steady-State Concurrency Execution**:
  - The suite uses Python's `concurrent.futures.ThreadPoolExecutor` to dispatch simultaneous requests simulating 1, 2, 4, and 8 concurrent client connections.
  - Each concurrency tier runs a controlled batch of steady-state requests.
  - Standardized payloads are used across tests:
    - **Translation**: 120-character English text.
    - **ASR**: 7.56-second 24kHz mono PCM WAV file (`audio_medium.wav`).
    - **TTS**: 105-character Nepali sentence (`speaker=Prakash_0`).

### Stage 4: Background Telemetry Monitoring Daemon
* During load execution, a dedicated background thread polls the GPU using NVML every 100 milliseconds:
  - GPU compute core utilization (`%`).
  - Active VRAM memory consumption (`MiB`).
  - Board power draw (`Watts`).
* When the test batch completes, telemetry data is synchronized with request timestamps to calculate average and peak resource utilization.

### Stage 5: Programmatic Aggregation & Report Generation
* **Aggregation**: Raw timestamps and telemetry logs are consolidated into `results/processed/<server_id>/summary.json`.
* **Visualization**: Clean, publication-grade SVG vector and 2x Lanczos-downsampled PNG charts are generated with embedded data tables to eliminate label collisions.
* **Documentation**: Markdown reports (`reports/july/`) and styled Word documents (`.docx`) are compiled automatically.

---

## 2. What the Metrics Mean: Metric Definitions & Interpretation

### 1. Overall Latency (ms)
* **What it is**: The mean (average) end-to-end elapsed time from the moment a client sends an HTTP request until the complete response (audio stream or JSON text) is received.
* **Formula**:
  $$\text{Overall Latency} = \frac{1}{N} \sum_{i=1}^{N} (t_{\text{response\_received}} - t_{\text{request\_sent}})$$
* **Why Overall Latency is used**: Rather than complicating executive reports with statistical percentiles (P50, P95, P99), overall latency provides a single, intuitive number representing the average wait time an end-user or client service experiences.
* **Interpretation**:
  - **WiseAI ASR (147.0 ms – 239.4 ms)**: Remains virtually instantaneous across concurrency tiers due to efficient parallel token decoding in vLLM.
  - **WiseAI TTS (337.2 ms – 1685.6 ms)**: Remains sub-second up to concurrency 4. Beyond concurrency 4, requests queue behind diffusion steps, increasing overall latency.
  - **WiseAI Translation (355.2 ms – 1580.2 ms)**: Grows linearly with concurrency because the current worker processes requests sequentially.

---

### 2. Throughput (req/s / RPS)
* **What it is**: The number of requests the service successfully completes per second under steady load.
* **Formula**:
  $$\text{Throughput} = \frac{\text{Total Successful Requests}}{\text{Total Wall-Clock Test Duration (seconds)}}$$
* **Interpretation**:
  - **Linear Scaling (Healthy)**: As concurrency doubles, throughput doubles (demonstrated by WiseAI ASR scaling from 6.80 req/s at C1 to 32.89 req/s at C8).
  - **Flat Scaling (Worker/Compute Bound)**: Throughput plateaus when hardware compute is saturated (WiseAI TTS at ~3.36 req/s) or when single-threaded worker queues serialize requests (WiseAI Translation at ~2.85 req/s).

---

### 3. Real-Time Factor (RTF) — Speech Services
* **What it is**: A standard speech processing metric measuring the ratio of processing time to the duration of the audio processed.
* **Formula**:
  $$\text{RTF} = \frac{\text{Processing Time (seconds)}}{\text{Audio Duration (seconds)}}$$
* **Thresholds**:
  - **RTF < 1.0**: Processing is **faster than real-time playback**.
  - **RTF = 1.0**: Processing matches real-time playback speed exactly.
  - **RTF > 1.0**: The system lags behind real-time playback, creating audio stutter in streaming or voice agent pipelines.
* **Interpretation**:
  - **WiseAI ASR (RTF = 0.019 – 0.032)**: Transcribes a 7.56-second audio snippet in ~0.15–0.24 seconds, operating **30x to 50x faster than real-time**.
  - **WiseAI TTS (RTF = 0.045 – 0.223)**: Generates 7.56 seconds of high-fidelity 24kHz audio in 0.34s to 1.68s, easily sustaining real-time speech interaction.

---

### 4. GPU Compute Utilization (%)
* **What it is**: The fraction of time within the sampling window during which one or more GPU CUDA kernels were actively executing.
* **Interpretation**:
  - **Low Utilization (< 30%) with High Latency**: Indicates a software queue bottleneck, I/O wait, or lack of worker concurrency (e.g. IndicTrans2 at ~25% GPU util).
  - **High Utilization (> 95%)**: Indicates the GPU is fully compute-bound (e.g. OmniVoice TTS flow-matching diffusion reaching 99.6%–100% compute).

---

### 5. Peak GPU Memory (VRAM) vs Headroom
* **What it is**: The maximum VRAM allocated by all active container processes on the GPU during the test run.
* **Baseline Allocation**: On server `mirage`, the baseline footprint for the co-located containers is **16,151 MiB / 24,576 MiB (65.7%)**.
* **Headroom**: Approximately **8,425 MiB (~8.4 GB)** remains unallocated.
* **Interpretation**: Dynamic KV-cache expansion during test execution raised peak memory to 16,355 MiB, confirming that a 24 GB card provides sufficient headroom for current workloads without risking Out-Of-Memory (OOM) errors.

---

### 6. Error Rate (%)
* **What it is**: The percentage of requests that failed, timed out, or returned an HTTP status other than 200 OK.
* **Result**: **0.0% error rate** across all tests, confirming zero packet loss or process crashes under load.

---

## 3. How to Reproduce on Other Servers

When migrating this repository to another server (e.g. staging or production GPU clusters):

```bash
# 1. Clone the repository
git clone git@github.com:Firoj-Wise/models_performance_report_gen.git
cd models_performance_report_gen

# 2. Run system discovery (captures GPU, CPU, and Docker setup)
./scripts/discover.sh

# 3. Validate service health & compatibility
./scripts/validate.sh

# 4. Run full benchmark suite (concurrency 1, 2, 4, 8)
./scripts/benchmark_all.sh

# 5. Generate updated SVG/PNG charts and Markdown/DOCX reports
./scripts/generate_report.sh
```

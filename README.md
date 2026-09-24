# WiseAI GPU Platform Validation & Scalability Benchmarking Framework

A standardized, reproducible benchmarking and compatibility engineering framework designed to validate GPU hardware, container stacks, and microservice inference performance across organization GPU servers.

---

## Deliverables

1. **June Report**: [`reports/june/gpu_platform_validation.md`](reports/june/gpu_platform_validation.md)  
   Formal platform validation, CUDA/driver compatibility, framework audits, and functional smoke testing matrix.
2. **July Report**: [`reports/july/performance_scalability.md`](reports/july/performance_scalability.md)  
   Steady-state performance profiling, concurrency ramps, overall response latency, throughput (RPS), Real-Time Factor (RTF), and GPU resource utilization.
3. **Charts**: [`results/charts/mirage/`](results/charts/mirage/)  
   Programmatically generated SVG vector charts for latency, throughput, GPU utilization, and RTF.
4. **Methodology & Metrics Guide**: [`docs/methodology_and_metrics.md`](docs/methodology_and_metrics.md)  
   Comprehensive explanation of how benchmarks are executed (discovery, warmup, load testing, telemetry) and what each metric (Overall Latency, Throughput RPS, RTF, GPU Compute %, VRAM Headroom) means.
5. **DevOps Questionnaire**: [`docs/devops_questions.md`](docs/devops_questions.md)  
   Discovered parameters and operational boundary questions.

---

## Directory Structure

```text
gpu-validation/
│
├── benchmark/
│   ├── discovery/         # Hardware & container topology discovery
│   ├── compatibility/     # GPU/CUDA/vLLM/PyTorch compatibility matrix
│   ├── benchmarks/        # Master test suite orchestrator
│   ├── load/              # Concurrency and load testing engine
│   ├── monitoring/        # Real-time background GPU/CPU telemetry collector
│   └── analysis/          # Chart rendering and markdown report generators
│
├── config/
│   └── manifest.yaml      # Machine-readable server benchmark manifest
│
├── data/
│   ├── audio/             # Standardized audio corpuses & metadata
│   └── text/              # Standardized Nepali / English text workloads
│
├── docs/
│   └── devops_questions.md# DevOps questionnaire and discovery log
│
├── results/
│   ├── raw/mirage/        # Raw JSON, CSV request logs, and telemetry
│   ├── processed/mirage/  # Aggregated metrics summaries
│   └── charts/mirage/     # Programmatic SVG visual charts
│
├── reports/
│   ├── june/              # June Platform Validation Report
│   └── july/              # July Performance & Scalability Report
│
├── scripts/               # CLI reproduction commands
│   ├── discover.sh
│   ├── validate.sh
│   ├── benchmark.sh
│   ├── benchmark_all.sh
│   └── generate_report.sh
│
└── README.md
```

---

## Quick Start (Reproduction Workflow)

### 1. Environment Discovery
Inspect host hardware, NVIDIA driver, CUDA versions, and running Docker containers:
```bash
./scripts/discover.sh
```

### 2. Compatibility & Functional Validation
Run the compatibility matrix and service smoke tests:
```bash
./scripts/validate.sh
```

### 3. Run Benchmark for a Single Service
Run a controlled load test for a specific service:
```bash
./scripts/benchmark.sh --service translation --workload medium --concurrency 4 --requests 8
./scripts/benchmark.sh --service asr --workload medium --concurrency 4 --requests 8
./scripts/benchmark.sh --service tts --workload medium --concurrency 4 --requests 8
```

### 4. Execute Full Benchmark Suite
Runs the complete matrix across all services, concurrency levels (1, 2, 4, 8), plots charts, and compiles reports:
```bash
./scripts/benchmark_all.sh
```

### 5. Re-generate Charts and Reports
```bash
./scripts/generate_report.sh
```

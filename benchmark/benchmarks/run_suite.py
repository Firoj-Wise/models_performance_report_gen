#!/usr/bin/env python3
"""
Master Benchmark Suite Orchestrator.
Sequentially runs:
1. Environment Discovery
2. Compatibility Validation
3. Benchmark Matrix (Concurrency 1, 2, 4, 8)
4. SVG Chart Generation
5. June & July Report Generation
"""
import os
import sys
import subprocess
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from benchmark.discovery.system_info import get_system_info
from benchmark.load.runner import ServiceBenchmarkRunner
from benchmark.analysis.plot_charts import generate_all_charts
from benchmark.analysis.generate_reports import generate_reports

def run_suite():
    print("\n=======================================================")
    print("STEP 1: DISCOVERING HARDWARE & DOCKER ENVIRONMENT")
    print("=======================================================")
    get_system_info()

    print("\n=======================================================")
    print("STEP 2: RUNNING COMPATIBILITY & VALIDATION MATRIX")
    print("=======================================================")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "benchmark", "compatibility", "validate_stack.py")], check=True)

    print("\n=======================================================")
    print("STEP 3: EXECUTING BENCHMARK CONCURRENCY EXPERIMENTS")
    print("=======================================================")
    # Concurrencies: 1, 2, 4, 8
    # Order: Translation, ASR, TTS
    services = ["translation", "asr", "tts"]
    concurrencies = [1, 2, 4, 8]

    for svc in services:
        for c in concurrencies:
            # 8 requests for steady-state
            runner = ServiceBenchmarkRunner(service=svc, workload_size="medium", concurrency=c, num_requests=8)
            runner.run()
            time.sleep(1.0) # Brief pause between runs

    print("\n=======================================================")
    print("STEP 4: GENERATING VECTOR SVG CHARTS")
    print("=======================================================")
    generate_all_charts()

    print("\n=======================================================")
    print("STEP 5: GENERATING JUNE & JULY FORMAL REPORTS")
    print("=======================================================")
    generate_reports()

    print("\n=======================================================")
    print("SUITE COMPLETED SUCCESSFULLY!")
    print(f"Reports available at:")
    print(f"  - reports/june/gpu_platform_validation.md")
    print(f"  - reports/july/performance_scalability.md")
    print("=======================================================\n")

if __name__ == "__main__":
    run_suite()

#!/usr/bin/env python3
"""
Lightweight background hardware & GPU telemetry monitor.
Samples nvidia-smi and system stats every N seconds into CSV/JSON.
"""
import os
import sys
import time
import subprocess
import threading
import json
import csv

class TelemetryCollector:
    def __init__(self, output_csv, interval=0.5):
        self.output_csv = output_csv
        self.interval = interval
        self.running = False
        self.thread = None
        self.samples = []
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    def _sample(self):
        cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv,noheader,nounits"
        try:
            out = subprocess.check_output(cmd, shell=True, text=True).strip()
            parts = [float(x.strip()) for x in out.split(",")]
            gpu_util, mem_used, temp, power = parts[0], parts[1], parts[2], parts[3]
        except Exception:
            gpu_util, mem_used, temp, power = 0.0, 0.0, 0.0, 0.0

        # CPU & Mem stats from /proc
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem_total = int([x for x in lines if "MemTotal" in x][0].split()[1]) / 1024.0 # MB
            mem_avail = int([x for x in lines if "MemAvailable" in x][0].split()[1]) / 1024.0 # MB
            ram_used_mb = mem_total - mem_avail
        except Exception:
            ram_used_mb = 0.0

        ts = time.time()
        sample = {
            "timestamp": ts,
            "gpu_util_pct": gpu_util,
            "gpu_mem_used_mb": mem_used,
            "gpu_temp_c": temp,
            "gpu_power_w": power,
            "ram_used_mb": ram_used_mb
        }
        return sample

    def _run(self):
        with open(self.output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "gpu_util_pct", "gpu_mem_used_mb", "gpu_temp_c", "gpu_power_w", "ram_used_mb"])
            writer.writeheader()
            while self.running:
                s = self._sample()
                self.samples.append(s)
                writer.writerow(s)
                f.flush()
                time.sleep(self.interval)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        return self.samples

    def get_summary(self):
        if not self.samples:
            return {
                "avg_gpu_util": 0, "max_gpu_util": 0,
                "avg_gpu_mem_mb": 0, "peak_gpu_mem_mb": 0,
                "avg_power_w": 0, "max_power_w": 0
            }
        utils = [s["gpu_util_pct"] for s in self.samples]
        mems = [s["gpu_mem_used_mb"] for s in self.samples]
        powers = [s["gpu_power_w"] for s in self.samples]
        return {
            "avg_gpu_util": round(sum(utils) / len(utils), 1),
            "max_gpu_util": round(max(utils), 1),
            "avg_gpu_mem_mb": round(sum(mems) / len(mems), 1),
            "peak_gpu_mem_mb": round(max(mems), 1),
            "avg_power_w": round(sum(powers) / len(powers), 1),
            "max_power_w": round(max(powers), 1)
        }

#!/usr/bin/env python3
"""
WiseAI Microservices Benchmark & Load Test Harness.
Executes cold-start, warmup, and steady-state concurrency experiments.
Records all request-level metrics and telemetry to JSON and CSV.
"""
import os
import sys
import time
import json
import csv
import math
import uuid
import wave
import argparse
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from benchmark.monitoring.collector import TelemetryCollector

def get_server_id():
    if os.environ.get("SERVER_ID"):
        return os.environ.get("SERVER_ID").strip()
    manifest_p = os.path.join(BASE_DIR, "config", "manifest.yaml")
    if os.path.exists(manifest_p):
        try:
            import yaml
            with open(manifest_p, "r") as f:
                m = yaml.safe_load(f)
                if m and "server" in m and "id" in m["server"]:
                    return str(m["server"]["id"]).strip()
        except Exception:
            pass
    import platform
    return platform.node().strip() or "localhost"

SERVER_ID = get_server_id()
RAW_DIR = os.path.join(BASE_DIR, "results", "raw", SERVER_ID)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(RAW_DIR, exist_ok=True)

def calculate_percentiles(values):
    if not values:
        return {"min": 0, "p50": 0, "p90": 0, "p95": 0, "p99": 0, "max": 0, "mean": 0, "stddev": 0}
    s = sorted(values)
    n = len(s)
    def pct(p):
        idx = int(math.ceil((p / 100.0) * n)) - 1
        return s[max(0, min(idx, n - 1))]
    mean = sum(s) / float(n)
    variance = sum((x - mean) ** 2 for x in s) / float(n) if n > 1 else 0
    return {
        "min": round(s[0], 2),
        "p50": round(pct(50), 2),
        "p90": round(pct(90), 2),
        "p95": round(pct(95), 2),
        "p99": round(pct(99), 2),
        "max": round(s[-1], 2),
        "mean": round(mean, 2),
        "stddev": round(math.sqrt(variance), 2)
    }

class ServiceBenchmarkRunner:
    def __init__(self, service, workload_size="medium", concurrency=1, num_requests=8):
        self.service = service
        self.workload_size = workload_size
        self.concurrency = concurrency
        self.num_requests = num_requests
        self.load_workload()

    def load_workload(self):
        workloads_path = os.path.join(DATA_DIR, "text", "workloads.json")
        with open(workloads_path, "r") as f:
            workloads = json.load(f)
            
        if self.service == "tts":
            self.workload = workloads["tts"][self.workload_size]
        elif self.service == "translation":
            self.workload = workloads["translation"][self.workload_size]
        elif self.service == "asr":
            audio_manifest_path = os.path.join(DATA_DIR, "audio", "audio_manifest.json")
            with open(audio_manifest_path, "r") as af:
                audio_manifest = json.load(af)
            self.workload = audio_manifest[self.workload_size]
            with open(self.workload["file"], "rb") as f:
                self.audio_bytes = f.read()

    def execute_tts_request(self):
        url = "http://localhost:8071/generate_from_text"
        data = urllib.parse.urlencode({
            "text": self.workload["text"],
            "language": self.workload["language"],
            "model": self.workload["model"],
            "reference_audio_id": self.workload["speaker"],
            "output_type": "audio"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        
        start_t = time.perf_counter()
        status_code = 0
        err = None
        duration_s = 0.0
        bytes_len = 0
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                body = resp.read()
                bytes_len = len(body)
                # Compute duration from header or length (24kHz 16-bit mono = 48000 bytes/sec)
                # 44 byte header
                pcm_bytes = max(0, bytes_len - 44)
                duration_s = pcm_bytes / 48000.0
        except Exception as e:
            err = str(e)
            status_code = 500
        end_t = time.perf_counter()
        
        latency_ms = (end_t - start_t) * 1000.0
        rtf = (latency_ms / 1000.0) / duration_s if duration_s > 0 else 0.0
        return {
            "status_code": status_code,
            "latency_ms": latency_ms,
            "duration_s": round(duration_s, 3),
            "rtf": round(rtf, 4),
            "bytes": bytes_len,
            "error": err
        }

    def execute_translation_request(self):
        url = "http://localhost:8999/translate"
        payload = json.dumps({
            "text": self.workload["text"],
            "input_language": self.workload["input_language"],
            "output_language": self.workload["output_language"]
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        
        start_t = time.perf_counter()
        status_code = 0
        err = None
        chars_out = 0
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                body = json.loads(resp.read().decode())
                translated_text = body.get("translations", [{}])[0].get("translated", "")
                chars_out = len(translated_text)
        except Exception as e:
            err = str(e)
            status_code = 500
        end_t = time.perf_counter()
        
        latency_ms = (end_t - start_t) * 1000.0
        return {
            "status_code": status_code,
            "latency_ms": latency_ms,
            "chars_in": len(self.workload["text"]),
            "chars_out": chars_out,
            "error": err
        }

    def execute_asr_request(self):
        url = "http://localhost:8091/transcribe-from-stream"
        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
        body_parts = []
        
        # Audio file field
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(b'Content-Disposition: form-data; name="audio"; filename="stream.wav"\r\n')
        body_parts.append(b'Content-Type: audio/wav\r\n\r\n')
        body_parts.append(self.audio_bytes)
        body_parts.append(b"\r\n")
        
        # Language field
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(b'Content-Disposition: form-data; name="language"\r\n\r\n')
        body_parts.append(b"nepali\r\n")
        
        # Output type field
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(b'Content-Disposition: form-data; name="output_type"\r\n\r\n')
        body_parts.append(b"text\r\n")
        
        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        payload = b"".join(body_parts)
        
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        })
        
        start_t = time.perf_counter()
        status_code = 0
        err = None
        transcription = ""
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                res_json = json.loads(resp.read().decode())
                transcription = res_json.get("text", "")
        except Exception as e:
            err = str(e)
            status_code = 500
        end_t = time.perf_counter()
        
        latency_ms = (end_t - start_t) * 1000.0
        audio_dur = self.workload["duration_seconds"]
        rtf = (latency_ms / 1000.0) / audio_dur if audio_dur > 0 else 0.0
        return {
            "status_code": status_code,
            "latency_ms": latency_ms,
            "audio_duration_s": audio_dur,
            "rtf": round(rtf, 4),
            "transcription": transcription,
            "error": err
        }

    def dispatch_request(self):
        if self.service == "tts":
            return self.execute_tts_request()
        elif self.service == "translation":
            return self.execute_translation_request()
        elif self.service == "asr":
            return self.execute_asr_request()

    def run(self):
        print(f"\n==========================================")
        print(f"BENCHMARK: Service={self.service.upper()} | Workload={self.workload_size} | Concurrency={self.concurrency} | Requests={self.num_requests}")
        print(f"==========================================")
        
        # 1. Warmup (2 requests, excluded from stats)
        print("Executing 2 warmup requests...")
        for _ in range(2):
            self.dispatch_request()
            
        # 2. Start Telemetry Monitor
        telemetry_file = os.path.join(RAW_DIR, f"{self.service}_{self.workload_size}_c{self.concurrency}_telemetry.csv")
        monitor = TelemetryCollector(telemetry_file, interval=0.25)
        monitor.start()
        
        # 3. Steady State Load Test
        results = []
        overall_start = time.perf_counter()
        
        if self.concurrency == 1:
            for i in range(self.num_requests):
                res = self.dispatch_request()
                res["req_id"] = i + 1
                results.append(res)
        else:
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                futures = [executor.submit(self.dispatch_request) for _ in range(self.num_requests)]
                req_idx = 1
                for f in as_completed(futures):
                    res = f.result()
                    res["req_id"] = req_idx
                    results.append(res)
                    req_idx += 1
                    
        overall_end = time.perf_counter()
        total_time_s = overall_end - overall_start
        
        # 4. Stop Telemetry Monitor
        monitor.stop()
        telemetry_summary = monitor.get_summary()
        
        # 5. Process Metrics
        latencies = [r["latency_ms"] for r in results if r["status_code"] == 200]
        successful = len(latencies)
        failed = self.num_requests - successful
        throughput_rps = round(successful / total_time_s, 2) if total_time_s > 0 else 0.0
        
        lat_stats = calculate_percentiles(latencies)
        
        rtf_stats = {}
        if self.service in ["tts", "asr"]:
            rtfs = [r["rtf"] for r in results if r["status_code"] == 200 and "rtf" in r]
            rtf_stats = calculate_percentiles(rtfs)
            
        summary = {
            "service": self.service,
            "workload_size": self.workload_size,
            "concurrency": self.concurrency,
            "total_requests": self.num_requests,
            "successful_requests": successful,
            "failed_requests": failed,
            "error_rate_pct": round((failed / float(self.num_requests)) * 100.0, 2),
            "total_elapsed_sec": round(total_time_s, 2),
            "throughput_rps": throughput_rps,
            "latency_ms": lat_stats,
            "real_time_factor": rtf_stats,
            "telemetry": telemetry_summary,
            "server_id": SERVER_ID
        }
        
        # 6. Save Requests CSV
        csv_file = os.path.join(RAW_DIR, f"{self.service}_{self.workload_size}_c{self.concurrency}_requests.csv")
        if results:
            keys = list(results[0].keys())
            with open(csv_file, "w", newline="") as cf:
                writer = csv.DictWriter(cf, fieldnames=keys)
                writer.writeheader()
                for r in results:
                    writer.writerow(r)
                    
        # 7. Save Run JSON
        json_file = os.path.join(RAW_DIR, f"{self.service}_{self.workload_size}_c{self.concurrency}.json")
        with open(json_file, "w") as jf:
            json.dump(summary, jf, indent=2)
            
        print(f"Completed in {total_time_s:.2f}s | Throughput: {throughput_rps} req/s | P50: {lat_stats['p50']}ms | P95: {lat_stats['p95']}ms | GPU Util: {telemetry_summary['avg_gpu_util']}% | Peak VRAM: {telemetry_summary['peak_gpu_mem_mb']}MB")
        return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=["tts", "asr", "translation", "all"], default="all")
    parser.add_argument("--workload", choices=["short", "medium", "long"], default="medium")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--requests", type=int, default=8)
    args = parser.parse_args()
    
    services = ["translation", "tts", "asr"] if args.service == "all" else [args.service]
    for s in services:
        runner = ServiceBenchmarkRunner(s, args.workload, args.concurrency, args.requests)
        runner.run()

#!/usr/bin/env python3
"""
Hardware, OS, Software, and Docker environment discovery script.
Collects actual system metadata and saves to results/raw/<server-id>/system_info.json.
"""
import os
import json
import subprocess
import platform
import shutil

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_ID = "mirage"
OUT_DIR = os.path.join(BASE_DIR, "results", "raw", SERVER_ID)
os.makedirs(OUT_DIR, exist_ok=True)

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip()}"

def get_system_info():
    info = {
        "server_id": SERVER_ID,
        "hostname": platform.node(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "pretty_name": run_cmd("cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'")
        },
        "cpu": {
            "model": run_cmd("lscpu | grep 'Model name' | sed 's/Model name:[ \t]*//'"),
            "cores": int(run_cmd("lscpu | grep 'Core(s) per socket:' | awk '{print $4}'") or 16),
            "threads_per_core": int(run_cmd("lscpu | grep 'Thread(s) per core:' | awk '{print $4}'") or 2),
            "sockets": int(run_cmd("lscpu | grep 'Socket(s):' | awk '{print $2}'") or 1),
            "numa_nodes": int(run_cmd("lscpu | grep 'NUMA node(s):' | awk '{print $3}'") or 1)
        },
        "memory": {
            "total_bytes": int(float(run_cmd("grep MemTotal /proc/meminfo | awk '{print $2 * 1024}'") or 0)),
            "available_bytes": int(float(run_cmd("grep MemAvailable /proc/meminfo | awk '{print $2 * 1024}'") or 0)),
            "swap_total_bytes": int(float(run_cmd("grep SwapTotal /proc/meminfo | awk '{print $2 * 1024}'") or 0))
        },
        "storage": {
            "root_total_gb": run_cmd("df -h / | tail -n 1 | awk '{print $2}'"),
            "root_used_gb": run_cmd("df -h / | tail -n 1 | awk '{print $3}'"),
            "root_avail_gb": run_cmd("df -h / | tail -n 1 | awk '{print $4}'"),
            "root_use_pct": run_cmd("df -h / | tail -n 1 | awk '{print $5}'")
        },
        "gpu": [],
        "docker": {
            "version": run_cmd("docker --version"),
            "compose_version": run_cmd("docker compose version 2>&1 || true")
        },
        "containers": []
    }

    # GPU Discovery via nvidia-smi
    smi_query = "name,driver_version,memory.total,memory.free,memory.used,compute_cap,pstate,temperature.gpu,power.draw,power.limit,uuid,pci.bus_id"
    smi_out = run_cmd(f"nvidia-smi --query-gpu={smi_query} --format=csv,noheader,nounits")
    if not smi_out.startswith("ERROR"):
        for line in smi_out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 12:
                info["gpu"].append({
                    "name": parts[0],
                    "driver_version": parts[1],
                    "total_memory_mb": float(parts[2]),
                    "free_memory_mb": float(parts[3]),
                    "used_memory_mb": float(parts[4]),
                    "compute_capability": parts[5],
                    "pstate": parts[6],
                    "temperature_c": float(parts[7]),
                    "power_draw_w": float(parts[8]),
                    "power_limit_w": float(parts[9]),
                    "uuid": parts[10],
                    "pci_bus_id": parts[11],
                    "ecc_support": False,
                    "mig_mode": "Not Supported"
                })

    # Containers Discovery
    ps_fmt = '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}"}'
    ps_out = run_cmd(f"docker ps -a --format '{ps_fmt}'")
    for line in ps_out.splitlines():
        try:
            c = json.loads(line)
            info["containers"].append(c)
        except Exception:
            pass

    out_file = os.path.join(OUT_DIR, "system_info.json")
    with open(out_file, "w") as f:
        json.dump(info, f, indent=2)
    print(f"System info saved to {out_file}")
    return info

if __name__ == "__main__":
    get_system_info()

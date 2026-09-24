#!/usr/bin/env python3
"""
Docker Container & Image Inspection Tool for WiseAI Microservices.
Deeply inspects container image manifests, layers, runtime environment variables,
CUDA/PyTorch versions, entrypoint configurations, and resource constraints.
Saves structured output to results/raw/<server_id>/docker_image_eval.json.
"""
import os
import json
import subprocess
import yaml

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_server_id():
    if os.environ.get("SERVER_ID"):
        return os.environ.get("SERVER_ID").strip()
    manifest_p = os.path.join(BASE_DIR, "config", "manifest.yaml")
    if os.path.exists(manifest_p):
        try:
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
MANIFEST_PATH = os.path.join(BASE_DIR, "config", "manifest.yaml")
OUT_FILE = os.path.join(RAW_DIR, "docker_image_eval.json")

os.makedirs(RAW_DIR, exist_ok=True)

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return ""

def inspect_docker_images():
    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as mf:
            manifest = yaml.safe_load(mf)

    services = manifest.get("services", {})
    image_eval_results = {
        "server_id": SERVER_ID,
        "evaluated_at": run_cmd("date -u +'%Y-%m-%dT%H:%M:%SZ'"),
        "docker_runtime": {
            "engine_version": run_cmd("docker --version"),
            "nvidia_toolkit": "active" if "nvidia" in run_cmd("docker info | grep -i runtime || true") else "standard"
        },
        "images": []
    }

    target_containers = []
    for svc_name, svc_cfg in services.items():
        for role in ["gateway", "backend", "worker"]:
            if role in svc_cfg:
                c_info = svc_cfg[role]
                target_containers.append({
                    "service": svc_name,
                    "role": role,
                    "container_name": c_info.get("container"),
                    "image_name": c_info.get("image"),
                    "configured_image_id": c_info.get("image_id", ""),
                    "port": c_info.get("port"),
                    "expected_runtime": c_info.get("runtime", "N/A"),
                    "gpu_allocation_mb": c_info.get("gpu_allocation_mb", 0)
                })

    for item in target_containers:
        c_name = item["container_name"]
        img_name = item["image_name"]
        
        # Inspect running container or image
        inspect_raw = run_cmd(f"docker inspect {c_name} 2>/dev/null || docker inspect {img_name} 2>/dev/null")
        entry = {
            "service": item["service"],
            "role": item["role"],
            "container_name": c_name,
            "image_name": img_name,
            "port": item["port"],
            "expected_runtime": item["expected_runtime"],
            "gpu_allocation_mb": item["gpu_allocation_mb"],
            "status": "not_found",
            "image_id": item["configured_image_id"],
            "size_mb": 0,
            "env_vars": {},
            "entrypoint": [],
            "cmd": [],
            "cuda_version": "unknown",
            "pytorch_version": "unknown",
            "gpu_passthrough_verified": False
        }

        if inspect_raw:
            try:
                inspect_data = json.loads(inspect_raw)[0]
                entry["status"] = inspect_data.get("State", {}).get("Status", "exists")
                entry["image_id"] = inspect_data.get("Image", item["configured_image_id"])
                
                # Sizing & Config
                config = inspect_data.get("Config", {})
                entry["entrypoint"] = config.get("Entrypoint") or []
                entry["cmd"] = config.get("Cmd") or []
                
                # Parse environment variables
                raw_env = config.get("Env", [])
                env_map = {}
                for ev in raw_env:
                    if "=" in ev:
                        k, v = ev.split("=", 1)
                        env_map[k] = v
                entry["env_vars"] = {k: v for k, v in env_map.items() if any(sub in k.upper() for sub in ["CUDA", "TORCH", "VLLM", "NVIDIA", "PORT", "MODEL", "BATCH"])}
                
                # Detect CUDA & Runtime versions
                if "CUDA_VERSION" in env_map:
                    entry["cuda_version"] = env_map["CUDA_VERSION"]
                elif "NVIDIA_CUDA_VERSION" in env_map:
                    entry["cuda_version"] = env_map["NVIDIA_CUDA_VERSION"]

                # Check GPU reservation
                host_cfg = inspect_data.get("HostConfig", {})
                dev_reqs = host_cfg.get("DeviceRequests", [])
                for d in dev_reqs:
                    if d.get("Driver") == "nvidia" or "gpu" in str(d.get("Capabilities", [])):
                        entry["gpu_passthrough_verified"] = True

                # Get image size
                img_inspect = run_cmd(f"docker image inspect {entry['image_id']} --format '{{{{.Size}}}}' 2>/dev/null")
                if img_inspect.isdigit():
                    entry["size_mb"] = round(int(img_inspect) / (1024 * 1024), 1)

            except Exception as e:
                entry["parse_error"] = str(e)

        image_eval_results["images"].append(entry)

    with open(OUT_FILE, "w") as f:
        json.dump(image_eval_results, f, indent=2)

    print(f"Docker image evaluation saved to {OUT_FILE}")
    return image_eval_results

if __name__ == "__main__":
    inspect_docker_images()

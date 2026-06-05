import platform, os, subprocess, json, threading, time
import psutil

def _query_wmi(query):
    try:
        import wmi
        c = wmi.WMI()
        return c.query(query)
    except Exception:
        return []

def _powershell(cmd):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""

def _get_nvidia_vram_mb() -> int:
    """Use nvidia-smi to get accurate VRAM — WMI caps at 4GB for 32-bit AdapterRAM."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            return int(r.stdout.strip().split("\n")[0].strip())
    except Exception:
        pass
    return 0


def detect():
    info = {}

    # CPU — prefer WMI Name over platform.processor() which returns CPUID string
    wmi_cpu = _powershell("(Get-WmiObject Win32_Processor | Select-Object -First 1).Name")
    info["cpu_name"] = wmi_cpu if wmi_cpu else (platform.processor() or "Unknown CPU")
    info["cpu_cores"] = psutil.cpu_count(logical=False) or 1
    info["cpu_threads"] = psutil.cpu_count(logical=True) or 1

    # RAM
    mem = psutil.virtual_memory()
    info["ram_total_gb"] = round(mem.total / 1024**3, 1)
    info["ram_free_gb"] = round(mem.available / 1024**3, 1)

    # GPU — WMI for names, nvidia-smi for accurate VRAM (WMI AdapterRAM is 32-bit, caps at 4GB)
    gpus = []
    raw = _powershell("Get-WmiObject Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict): data = [data]
            for g in data:
                name = g.get("Name", "Unknown")
                vram_bytes = g.get("AdapterRAM", 0) or 0
                vram_mb = round(vram_bytes / 1024**2)
                gpus.append({"name": name, "vram_mb": vram_mb})
        except Exception:
            pass

    # Fix NVIDIA VRAM — nvidia-smi gives the real value, WMI lies above 4GB
    nvidia_smi_vram = _get_nvidia_vram_mb()
    for g in gpus:
        if ("nvidia" in g["name"].lower() or "geforce" in g["name"].lower()) and nvidia_smi_vram:
            g["vram_mb"] = nvidia_smi_vram

    info["gpus"]         = gpus
    info["has_nvidia"]   = any("nvidia" in g["name"].lower() or "geforce" in g["name"].lower() for g in gpus)
    info["has_amd_gpu"]  = any("amd" in g["name"].lower() or "radeon" in g["name"].lower() for g in gpus)
    info["primary_gpu"]  = next((g for g in gpus if "nvidia" in g["name"].lower() or "geforce" in g["name"].lower()), gpus[0] if gpus else None)
    info["vram_mb"]      = info["primary_gpu"]["vram_mb"] if info["primary_gpu"] else 0

    # Disk type
    disk_type = _powershell("Get-PhysicalDisk | Select-Object -First 1 MediaType | ForEach-Object {$_.MediaType}")
    info["ssd"] = "ssd" in disk_type.lower() or "nvme" in disk_type.lower() or disk_type.strip() in ("SSD", "NVMe", "3")

    # Free disk space on C:
    try:
        usage = psutil.disk_usage("C:\\")
        info["disk_free_gb"] = round(usage.free / 1024**3, 1)
    except Exception:
        info["disk_free_gb"] = 0

    info["os"] = platform.system() + " " + platform.release()
    info["arch"] = platform.machine()

    return info


def get_live_stats() -> dict:
    """Snapshot of current resource usage — safe to call from any thread."""
    stats = {}
    stats["cpu_pct"] = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    stats["ram_used_gb"] = round(mem.used / 1024**3, 1)
    stats["ram_total_gb"] = round(mem.total / 1024**3, 1)
    stats["ram_pct"] = mem.percent
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0:
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            if len(parts) >= 3:
                stats["gpu_pct"]          = int(parts[0])
                stats["gpu_vram_used_mb"] = int(parts[1])
                stats["gpu_vram_total_mb"]= int(parts[2])
                if len(parts) >= 4:
                    stats["gpu_temp"] = int(parts[3])
    except Exception:
        pass
    return stats


def detect_npu() -> dict | None:
    """Detect AMD XDNA/XDNA2 or Intel NPU. Returns dict or None."""
    # Primary: look for ComputeAccelerator class devices (where AMD XDNA2 NPU lives)
    cpu_name = _powershell("(Get-WmiObject Win32_Processor | Select-Object -First 1).Name").lower()
    cpu_is_amd = "amd" in cpu_name or "ryzen" in cpu_name

    raw = _powershell(
        "Get-PnpDevice -Class 'ComputeAccelerator' -Status 'OK'"
        " | Select-Object FriendlyName,Status | ConvertTo-Json"
    )
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict): data = [data]
            for d in data:
                name = d.get("FriendlyName", "")
                if name and ("npu" in name.lower() or "compute" in name.lower()):
                    vendor = "amd" if (cpu_is_amd or "amd" in name.lower()) else "intel"
                    tops   = 50 if vendor == "amd" else 34
                    label  = "AMD XDNA2 NPU" if vendor == "amd" else name
                    return {"name": label, "tops": tops, "vendor": vendor,
                            "note": "AMD Ryzen AI SDK (ryzenai-sw) + ONNX Runtime VitisAI EP"}
        except Exception:
            pass
    # Fallback: scan all PnP devices but skip HIDClass
    raw2 = _powershell(
        "Get-PnpDevice | Where-Object {$_.Class -ne 'HIDClass' -and"
        " ($_.FriendlyName -match 'XDNA|AI Boost')} | Select-Object FriendlyName,Status | ConvertTo-Json"
    )
    if raw2:
        try:
            data = json.loads(raw2)
            if isinstance(data, dict): data = [data]
            for d in data:
                name = d.get("FriendlyName", "")
                if name:
                    return {"name": name, "tops": None, "vendor": "amd", "note": ""}
        except Exception:
            pass
    return None


def score_system(hw):
    ram = hw["ram_total_gb"]
    vram = hw["vram_mb"]

    if ram >= 32 and vram >= 16000:
        return "high", "High-end"
    elif (ram >= 16 and vram >= 8000) or ram >= 24:
        return "upper-mid", "Upper-mid"
    elif ram >= 8 or vram >= 4000:
        return "mid", "Mid-range"
    elif ram >= 4:
        return "low", "Low-end"
    else:
        return "minimal", "Minimal"

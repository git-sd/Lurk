"""Manages the llama.cpp server process."""
import os, sys, subprocess, time, threading, platform, zipfile, io
from pathlib import Path
import requests

APP_DIR = Path.home() / "LURK"
BIN_DIR = APP_DIR / "bin"
BIN_DIR.mkdir(parents=True, exist_ok=True)

SERVER_PORT = 8765
_proc: subprocess.Popen | None = None

def _server_exe() -> Path:
    return BIN_DIR / ("llama-server.exe" if platform.system() == "Windows" else "llama-server")


def download_server(status_cb=None) -> bool:
    """Download pre-built llama-server from llama.cpp GitHub releases."""
    exe = _server_exe()
    if exe.exists():
        return True

    # Latest stable release for Windows
    api_url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    try:
        if status_cb: status_cb("Fetching latest llama.cpp release info...")
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        release = resp.json()

        # Find the right asset
        system = platform.system().lower()
        machine = platform.machine().lower()

        assets = release.get("assets", [])

        def match(name: str, kws: list) -> bool:
            name = name.lower()
            return all(k in name for k in kws) and name.endswith(".zip")

        def has_nvidia() -> bool:
            try:
                import subprocess
                r = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
                return r.returncode == 0
            except Exception:
                return False

        asset = None
        if system == "windows":
            # Prefer CUDA build for NVIDIA GPUs — much faster than Vulkan
            if has_nvidia():
                if status_cb: status_cb("NVIDIA GPU detected — looking for CUDA build...")
                asset = next((a for a in assets if match(a["name"], ["win", "cuda", "x64"])), None)
            if not asset:
                asset = next((a for a in assets if match(a["name"], ["win", "vulkan", "x64"])), None)
            if not asset:
                asset = next((a for a in assets if match(a["name"], ["win", "x64", "avx2"])), None)
            if not asset:
                asset = next((a for a in assets if match(a["name"], ["win", "x64"])), None)
        elif system == "linux":
            if has_nvidia():
                asset = next((a for a in assets if match(a["name"], ["linux", "cuda", "x86_64"])), None)
            if not asset:
                asset = next((a for a in assets if match(a["name"], ["linux", "x86_64", "avx2"])), None)
            if not asset:
                asset = next((a for a in assets if match(a["name"], ["linux", "x86_64"])), None)
        else:
            asset = next((a for a in assets if match(a["name"], ["macos"])), None)

        if not asset:
            asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if not asset:
            return False

        if status_cb: status_cb(f"Downloading {asset['name']} ({round(asset['size']/1024/1024, 1)} MB)...")
        r = requests.get(asset["browser_download_url"], stream=True, timeout=60)
        r.raise_for_status()

        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        buf = io.BytesIO()
        for chunk in r.iter_content(chunk_size=1024 * 256):
            buf.write(chunk)
            downloaded += len(chunk)
            if status_cb and total:
                pct = round(downloaded / total * 100)
                status_cb(f"Downloading llama-server... {pct}%")

        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            for name in z.namelist():
                base = os.path.basename(name)
                if base in ("llama-server.exe", "llama-server"):
                    with z.open(name) as src, open(exe, "wb") as dst:
                        dst.write(src.read())
                    if system != "windows":
                        exe.chmod(0o755)
                    if status_cb: status_cb("llama-server installed.")
                    return True

        return False
    except Exception as e:
        if status_cb: status_cb(f"Error downloading llama-server: {e}")
        return False


def start(model_path: str, gpu_layers: int = 99, ctx: int = 16384, log_cb=None) -> bool:
    global _proc
    stop()  # kills _proc + any orphan on the port
    time.sleep(0.5)  # brief wait for port to be released

    exe = _server_exe()
    if not exe.exists():
        return False

    import os
    threads = max(4, (os.cpu_count() or 4) - 2)

    cmd = [
        str(exe),
        "--model", model_path,
        "--host", "127.0.0.1",
        "--port", str(SERVER_PORT),
        "--ctx-size", str(ctx),
        "--threads", str(threads),
        "--n-gpu-layers", str(gpu_layers),
        "--flash-attn", "on",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
    ]

    # Add bin dir to PATH so all DLLs (ggml-vulkan.dll etc.) are found
    env = os.environ.copy()
    env["PATH"] = str(BIN_DIR) + os.pathsep + env.get("PATH", "")

    _proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )

    ready_event = threading.Event()
    failed_event = threading.Event()

    READY_STRINGS = ("listening", "server is listening", "http server listening", "all slots are idle")

    def reader():
        for line in _proc.stdout:
            line = line.rstrip()
            if log_cb:
                log_cb(line)
            if any(s in line.lower() for s in READY_STRINGS):
                ready_event.set()
        # stdout closed = process exited
        failed_event.set()

    threading.Thread(target=reader, daemon=True).start()

    # Poll until ready, crashed, or 90s timeout
    deadline = time.time() + 90
    while time.time() < deadline:
        if ready_event.is_set():
            return True
        if failed_event.is_set() or _proc.poll() is not None:
            return False
        time.sleep(0.2)

    return False


def stop():
    global _proc
    if _proc:
        try:
            _proc.terminate()
            _proc.wait(timeout=5)
        except Exception:
            try: _proc.kill()
            except Exception: pass
        _proc = None
    # Also kill any orphaned llama-server on our port (from crashed previous sessions)
    _kill_port(SERVER_PORT)


def _kill_port(port: int):
    """Kill any process occupying the given port."""
    try:
        import psutil
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.pid:
                try:
                    psutil.Process(conn.pid).kill()
                except Exception:
                    pass
    except Exception:
        pass


def is_running() -> bool:
    return _proc is not None and _proc.poll() is None


def base_url() -> str:
    return f"http://127.0.0.1:{SERVER_PORT}"

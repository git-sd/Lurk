"""Fan control — spins fans up when AI generates, back down when done."""
import subprocess, json, shutil, threading
from pathlib import Path

_CONFIG  = Path.home() / "LURK" / "config.json"
_PS      = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
_lock    = threading.Lock()
_orig_min: list = [None]   # remember the AC minimum % before we changed it


def _cfg() -> dict:
    try:
        return json.loads(_CONFIG.read_text())
    except Exception:
        return {}


def _ps(cmd: str) -> str:
    try:
        r = subprocess.run(_PS + [cmd], capture_output=True, text=True, timeout=8,
                           creationflags=0x08000000)
        return r.stdout.strip()
    except Exception:
        return ""


def _run(cmd: str) -> None:
    if not cmd:
        return
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=0x08000000)
    except Exception:
        pass


def _get_cpu_min_ac() -> int | None:
    out = _ps("powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN")
    for line in out.splitlines():
        if "AC Power Setting Index" in line:
            try:
                return int(line.strip().split()[-1], 16)
            except Exception:
                pass
    return None


def _set_cpu_min_ac(pct: int) -> None:
    _ps(f"powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN {pct}; "
        f"powercfg /setactive SCHEME_CURRENT")


def on() -> None:
    cfg = _cfg()
    if cfg.get("fan_on_cmd"):
        _run(cfg["fan_on_cmd"])
        return
    # Default: force CPU to 100% min frequency → heat → fans spin
    with _lock:
        if _orig_min[0] is None:
            _orig_min[0] = _get_cpu_min_ac() or 80
        _set_cpu_min_ac(100)


def off() -> None:
    cfg = _cfg()
    if cfg.get("fan_off_cmd"):
        _run(cfg["fan_off_cmd"])
        return
    # Restore original CPU min frequency
    with _lock:
        orig = _orig_min[0]
        if orig is not None:
            _set_cpu_min_ac(orig)
            _orig_min[0] = None


def set_commands(on_cmd: str, off_cmd: str) -> None:
    try:
        data = _cfg()
        data["fan_on_cmd"]  = on_cmd
        data["fan_off_cmd"] = off_cmd
        _CONFIG.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def clear_commands() -> None:
    try:
        data = _cfg()
        data.pop("fan_on_cmd",  None)
        data.pop("fan_off_cmd", None)
        _CONFIG.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def status() -> dict:
    cfg = _cfg()
    cur = _get_cpu_min_ac()
    return {
        "on_cmd":      cfg.get("fan_on_cmd",  ""),
        "off_cmd":     cfg.get("fan_off_cmd", ""),
        "nbfc":        shutil.which("nbfc") is not None,
        "cpu_min_pct": cur,
        "orig_min":    _orig_min[0],
    }

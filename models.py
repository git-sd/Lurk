import os, json, requests, threading, shutil
from pathlib import Path

APP_DIR = Path.home() / "LURK"
MODELS_DIR = APP_DIR / "models"
CONFIG_FILE = APP_DIR / "config.json"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Migrate models from old AppData location (Windows Store Python VFS fix)
_OLD_MODELS = Path(os.environ.get("APPDATA", "")) / "LURK" / "models"
if _OLD_MODELS.exists() and _OLD_MODELS.resolve() != MODELS_DIR.resolve():
    for _f in _OLD_MODELS.glob("*.gguf"):
        _dest = MODELS_DIR / _f.name
        if not _dest.exists() and _f.is_file() and _f.stat().st_size > 1024 * 1024:
            try:
                shutil.move(str(_f), str(_dest))
            except Exception:
                pass

REGISTRY = [
    {
        "id": "tinyllama-1.1b-q4",
        "name": "TinyLlama 1.1B Q4",
        "desc": "Ultra-lightweight. Runs on anything.",
        "repo": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        "file": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size_gb": 0.7,
        "min_ram_gb": 2,
        "min_vram_mb": 0,
        "tier": "low",
        "ctx": 2048,
        "tags": ["fast", "tiny", "cpu"],
    },
    {
        "id": "llama3.2-3b-q4",
        "name": "Llama 3.2 3B Q4",
        "desc": "Smart and fast. Great for most tasks.",
        "repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_gb": 2.0,
        "min_ram_gb": 4,
        "min_vram_mb": 0,
        "tier": "low",
        "ctx": 8192,
        "tags": ["balanced", "tool-use"],
    },
    {
        "id": "qwen2.5-7b-q4",
        "name": "Qwen 2.5 7B Q4",
        "desc": "Top-tier coding & reasoning. Tool use.",
        "repo": "bartowski/Qwen2.5-7B-Instruct-GGUF",
        "file": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.5,
        "min_ram_gb": 8,
        "min_vram_mb": 0,
        "tier": "mid",
        "ctx": 32768,
        "tags": ["coding", "reasoning", "tool-use"],
    },
    {
        "id": "llama3.1-8b-q4",
        "name": "Llama 3.1 8B Q4",
        "desc": "Meta flagship. Strong general purpose.",
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
        "min_ram_gb": 8,
        "min_vram_mb": 0,
        "tier": "mid",
        "ctx": 131072,
        "tags": ["general", "tool-use", "long-context"],
    },
    {
        "id": "mistral-7b-q4",
        "name": "Mistral 7B v0.3 Q4",
        "desc": "Fast, sharp, great instruction following.",
        "repo": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "file": "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        "size_gb": 4.4,
        "min_ram_gb": 8,
        "min_vram_mb": 0,
        "tier": "mid",
        "ctx": 32768,
        "tags": ["fast", "tool-use"],
    },
    {
        "id": "deepseek-r1-8b-q4",
        "name": "DeepSeek R1 8B Q4",
        "desc": "Reasoning model. Thinks before answering.",
        "repo": "lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF",
        "file": "DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf",
        "size_gb": 5.2,
        "min_ram_gb": 10,
        "min_vram_mb": 0,
        "tier": "mid",
        "ctx": 32768,
        "tags": ["reasoning", "coding", "math"],
    },
    {
        "id": "llama3.1-70b-q3",
        "name": "Llama 3.1 70B Q3",
        "desc": "Near GPT-4 quality. Needs beefy machine.",
        "repo": "bartowski/Meta-Llama-3.1-70B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-70B-Instruct-Q3_K_M.gguf",
        "size_gb": 29.0,
        "min_ram_gb": 32,
        "min_vram_mb": 8000,
        "tier": "high",
        "ctx": 131072,
        "tags": ["powerful", "gpt4-level"],
    },
]


def recommend(hw: dict) -> list:
    ram = hw["ram_total_gb"]
    vram = hw["vram_mb"]

    candidates = []
    for m in REGISTRY:
        if m["min_ram_gb"] > ram:
            continue
        if m["min_vram_mb"] > vram + ram * 200:
            continue
        score = 0
        if m["min_ram_gb"] <= ram * 0.6:
            score += 3
        elif m["min_ram_gb"] <= ram * 0.8:
            score += 2
        else:
            score += 1
        if hw.get("has_nvidia") and vram >= m["size_gb"] * 900:
            score += 2
        if hw.get("ssd"):
            score += 1
        candidates.append((score, m))

    candidates.sort(key=lambda x: -x[0])
    return [m for _, m in candidates[:4]]


def get_local_models() -> list:
    if not MODELS_DIR.exists():
        return []
    # Clean up any leftover partial downloads
    for p in MODELS_DIR.glob("*.part"):
        p.unlink(missing_ok=True)
    result = []
    for f in MODELS_DIR.glob("*.gguf"):
        if not f.is_file() or f.stat().st_size < 1024 * 1024:
            continue
        meta = next((m for m in REGISTRY if m["file"] == f.name), None)
        result.append({
            "path": str(f),
            "file": f.name,
            "name": meta["name"] if meta else f.name,
            "id": meta["id"] if meta else f.name,
            "size_gb": round(f.stat().st_size / 1024**3, 2),
        })
    return result


def download_model(model_id: str, progress_cb=None) -> Path:
    m = next((x for x in REGISTRY if x["id"] == model_id), None)
    if not m:
        raise ValueError(f"Unknown model: {model_id}")

    dest = MODELS_DIR / m["file"]
    if dest.exists() and dest.stat().st_size > 1024 * 1024:
        return dest

    # Write to .part file — only rename to final name when fully complete
    part = MODELS_DIR / (m["file"] + ".part")
    url = f"https://huggingface.co/{m['repo']}/resolve/main/{m['file']}"

    try:
        with requests.get(url, stream=True, timeout=(30, 300)) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(part, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        progress_cb(downloaded, total)
    except Exception:
        if part.exists():
            part.unlink()
        raise

    part.rename(dest)
    return dest


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

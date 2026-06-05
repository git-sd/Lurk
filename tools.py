"""Tool implementations — shell, filesystem, search."""
import os, subprocess, glob as _glob, platform
from pathlib import Path

def run_command(command: str, cwd: str = None) -> str:
    shell = "powershell.exe" if platform.system() == "Windows" else "/bin/bash"
    flag = "-Command" if platform.system() == "Windows" else "-c"
    try:
        r = subprocess.run(
            [shell, flag, command],
            capture_output=True, text=True,
            timeout=30, cwd=cwd or os.getcwd()
        )
        out = r.stdout.strip()
        err = r.stderr.strip()
        result = out
        if err:
            result += ("\n" if result else "") + f"[stderr]\n{err}"
        return result or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Error: {e}"


def read_file(path: str) -> str:
    p = Path(path.replace("~", str(Path.home())))
    if not p.exists():
        return f"File not found: {p}"
    if not p.is_file():
        return f"Not a file: {p}"
    try:
        text = p.read_text(errors="replace")
        if len(text) > 8000:
            return text[:8000] + f"\n... (truncated, {len(text)} total chars)"
        return text
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    p = Path(path.replace("~", str(Path.home())))
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {p}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_directory(path: str = ".") -> str:
    p = Path(path.replace("~", str(Path.home())))
    if not p.exists():
        return f"Directory not found: {p}"
    try:
        entries = []
        for item in sorted(p.iterdir()):
            prefix = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                s = item.stat().st_size
                size = f"  ({_fmt_size(s)})"
            entries.append(f"{prefix} {item.name}{size}")
        return "\n".join(entries) if entries else "(empty directory)"
    except PermissionError:
        return f"Permission denied: {p}"


def search_files(pattern: str, path: str = ".") -> str:
    base = Path(path.replace("~", str(Path.home())))
    try:
        matches = list(base.rglob(pattern))[:50]
        if not matches:
            return f"No files matching '{pattern}' in {base}"
        return "\n".join(str(m) for m in matches)
    except Exception as e:
        return f"Error: {e}"


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


TOOLS_SCHEMA = [
    {
        "name": "run_command",
        "description": "Execute a shell command (PowerShell on Windows). Returns stdout/stderr.",
        "params": {"command": "str — the command to run", "cwd": "str (optional) — working directory"}
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "params": {"path": "str — absolute or relative path to the file"}
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates parent dirs if needed).",
        "params": {"path": "str — file path", "content": "str — content to write"}
    },
    {
        "name": "list_directory",
        "description": "List files and folders in a directory.",
        "params": {"path": "str — directory path (default: current dir)"}
    },
    {
        "name": "search_files",
        "description": "Recursively search for files matching a glob pattern.",
        "params": {"pattern": "str — glob pattern e.g. '*.py'", "path": "str — base directory (default: current dir)"}
    },
]


def dispatch(name: str, args: dict) -> str:
    fns = {
        "run_command": lambda a: run_command(a.get("command", ""), a.get("cwd")),
        "read_file": lambda a: read_file(a.get("path", "")),
        "write_file": lambda a: write_file(a.get("path", ""), a.get("content", "")),
        "list_directory": lambda a: list_directory(a.get("path", ".")),
        "search_files": lambda a: search_files(a.get("pattern", "*"), a.get("path", ".")),
    }
    fn = fns.get(name)
    if fn:
        return fn(args)
    return f"Unknown tool: {name}"

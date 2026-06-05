"""Persistent learnings — stored as markdown files in ~/LURK/learnings/."""
import re
from pathlib import Path

LEARNINGS_DIR = Path.home() / "LURK" / "learnings"
LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)


def _safe(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.strip().lower())[:50] or "untitled"


def list_all() -> list[Path]:
    return sorted(LEARNINGS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def load(name: str) -> str:
    p = LEARNINGS_DIR / f"{_safe(name)}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def save(name: str, content: str) -> Path:
    p = LEARNINGS_DIR / f"{_safe(name)}.md"
    p.write_text(content.strip() + "\n", encoding="utf-8")
    return p


def delete(name: str) -> bool:
    p = LEARNINGS_DIR / f"{_safe(name)}.md"
    if p.exists():
        p.unlink()
        return True
    return False


def build_context(names: list[str]) -> str:
    """Return a system-prompt block from selected learning names."""
    parts = []
    for name in names:
        content = load(name)
        if content.strip():
            parts.append(f"=== {name} ===\n{content.strip()}")
    if not parts:
        return ""
    return "You have been taught the following by the user:\n\n" + "\n\n".join(parts)

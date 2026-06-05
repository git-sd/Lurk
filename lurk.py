#!/usr/bin/env python3
"""Lurk — Local AI terminal assistant. By Shreyan Das."""
import sys, os, re, time, threading, platform
import pyfiglet
import psutil
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.rule import Rule
from rich.live import Live
import hardware, models, server, inference

console = Console()

# ─── Theme (Rich pre-chat screens) ────────────────────────────────────────────

C_PRIMARY   = "medium_purple"
C_ACCENT    = "white"
C_DIM       = "grey42"
C_SUCCESS   = "white"
C_WARN      = "medium_purple"
C_ERROR     = "white"

# ─── Doge ASCII Portrait (64×32, rendered in purple) ─────────────────────────

DOGE_CHARS = [
    '@@@@@@@@@@@@@@@@@@@@@##@@@@@@@@@@@@@@@@@@@@@@#####@@@@@@@@@@@@@@',
    '@@@@@@@@@@@@@@@@@@###@@#@@@@@@@@@@@@@@@@@@@##@@@@@#@@@@@@@@@@@@@',
    '@@@@@@@@@@@@@@@@@#0xxX#@#@@@@@@@@@@@@@@@@##@@#XXX#@#@@@@@@@@@@@@',
    '@@@@@@@@@@@@@@@#@#00ooO#@#####@@@@@@@@@@#@@#0xxoox###@@@@@@@@@@@',
    '@@@@@@@@@@@@@@@#@#0Oo*=O#@@@@@@########@@#0xxxxxx=O@#@@@@@@@@@@@',
    '@@@@@@@@@@@@@@@###0xxo*=xX#####@@@@@@@@#XOxxxoooxoo#@@@@@@@@@@@@',
    '@@@@@@@@@@@####@@XxxxOOxxxxxxxOOOO00XXXOooxxooooxxo#@#@@@@@@@@@@',
    '@@@@@@@@@##@@@@#XOO0000Oxxxxxxxxxxxxxooooxxx==*=xxo#@#@@@@@@@@@@',
    '@@@@@@@@#@@#XX000000000xxxxxxxxxxxxxxxooxxxo=**ox=x##@@@@@@@@@@@',
    '@@@@@@@#@#X0000000O000xxxxxxOOxxxxxxxxxxxxo**=xxooX@#@@@@@@@@@@@',
    '@@@@@@#@#0O0000OxOxOOxxxxxO0000OxxxxxxxxxxxooxxxxxO#@#@@@@@@@@@@',
    '@@@@@@##X0XX00=,.;xxxxxxxO00000Oxxxxxxxxxxxxxxxxxxxx#@#@@@@@@@@@',
    '@@@@@#@XX###XO*  :xxxxxOxx00xxo+=xxxxxxxxxxxxxxxxxxxO##@@@@@@@@@',
    '@@@@@@######0OOxoOxOOO0Oxxx+OO,  ;xxxOOO0OxxOOxxxxxxxX@#@@@@@@@@',
    '@@@@@@######XXXXX000000xxxo+xO;:+oxxX#########XOxxxxx0##@@@@@@@@',
    '@@@@@######Xx==oox00000O00xxoxxxOOX############XOxxxxO@#@@@@@@@@',
    '@@@@######0.   .  ,0#XXX000XXXXX################Oxxxxx#@#@@@@@@@',
    '@@@@######X;   .  ,O@###X0X#####################OxxxxxO##@@@@@@@',
    '@@@@#####0=*,..:+*x#####00X#####################0xxxxxxX@#@@@@@@',
    '@@@@#####Xx==**===x####000X#########XXXXXXXXXXXOxxxxxxxO@#@@@@@@',
    '@@@@#######o++;++*xXXX000O0XXXXXXXXXXXXXXXXXXXXxxxxxxxxOX##@@@@@',
    '@@@@@#####X0OOxxoo==ooxOOO00XXXXXXXXX000XXXXX0xxxxxoxxxx0#@#@@@@',
    '@@@@@######X000XXXX00000XX0XXXXXXXX00XXXXXXXX0xxxooxxxxx0X#@@@@@',
    '@@@@@@#XXX0000000000XXXXXXXXXXXXX0000XXXXXX0xxxoooxxxxxx0X@@@@@@',
    '@@@@@#@X000000000000XXXXXXXXX000000XXXXXXXXOOxooooxxxxx0X0#@#@@@',
    '@@@@#@#X000000000000000XXXXX000000XX0XXXXXXOxooooxxxOO000xO@#@@@',
    '@@@@#@#XXX000000000000000000000000XXXXXXXXXX0oooxxx0XX0XOox#@#@@',
    '@@@@@#XXXXX000OOOOOOOOOOOOOOO0000XXXXXXXXXX0xxxO00X000X0ooo#@#@@',
    '@@@#@#XXXXXXX000OOOOOOOOOO00000000000000000000XXXXXX00XOoooX@#@@',
    '@@@#@#XXXXXXXXX00000OOOO00000000000000000000XXXXXXXXX0XOooo0@#@@',
    '@@@@#XXXXXXXXXXX0000OOO0000000000000000000XXXXXXXXXXX0xooooO@#@@',
    '@@#@#XXXXXXXXXXXXX0X000X000000000000000XXXXXXXXXXXXXOxooxxo0@#@@',
]

# Inverted greyscale: dark original pixels (outline, eyes) → bright on black bg.
# White background ('@') is skipped entirely so it never gets a colour.
_LURK_CHARS = ' .,:;+*=oxO0X#@'
_LURK_GREY = [
    "#ffffff", "#f5f5f5", "#ebebeb", "#e0e0e0",  # 0-3  darkest orig → bright
    "#d4d4d4", "#c8c8c8", "#bcbcbc", "#b0b0b0",  # 4-7  mid-dark
    "#a4a4a4", "#989898", "#8c8c8c", "#808080",  # 8-11 mid-bright
    "#747474", "#686868", "#060606",             # 12-14 lightest orig → bg (skipped)
]

def _lurk_color(ch: str) -> str:
    idx = _LURK_CHARS.find(ch)
    return _LURK_GREY[idx if idx >= 0 else 7]


def _doge_text(chars_list: list) -> "Text":
    """Render doge chars as Rich Text, '@' (white bg) becomes invisible space."""
    from rich.text import Text as RText
    t = RText()
    for row in chars_list:
        for ch in row:
            if ch == '@':
                t.append(' ')
            else:
                t.append(ch, style=_lurk_color(ch))
        t.append('\n')
    return t


# ─── Fullscreen splash (replaces print_banner + run_hardware_scan) ─────────────

def show_splash(hw: dict, npu: dict | None) -> None:
    import shutil, random
    from rich.text import Text as RT

    W  = shutil.get_terminal_size((180, 50)).columns
    IW = W - 2   # inner width

    MEMES = [
        "No cloud, just dog.",
        "Lurk mode: engaged.",
        "I see everything. Locally.",
        "No Wi-Fi? No problem.",
        "fully offline. fully unhinged.",
        "your data stays here. always.",
        "no packets sent. ever.",
    ]

    # ── Box helpers ──────────────────────────────────────────────────────────
    def hline(l="╠", m="═", r="╣"):
        console.print(RT(l + m * IW + r, style=C_PRIMARY))

    def brow(content: RT):
        line = RT("║ ", style=C_PRIMARY)
        line.append_text(content)
        line.append(" " * max(0, IW - 1 - len(content.plain)))
        line.append("║", style=C_PRIMARY)
        console.print(line)

    def blank():
        brow(RT(""))

    # ── LURK figlet ───────────────────────────────────────────────────────────
    fig_lines: list[str] = ["", "  L U R K", ""]
    for font in ["banner3", "block", "big", "standard"]:
        try:
            raw  = pyfiglet.figlet_format("LURK", font=font)
            lines = raw.splitlines()
            max_w = max((len(l) for l in lines), default=0)
            if lines and max_w < IW // 2:
                fig_lines = lines
                break
        except Exception:
            continue

    fig_h = len(fig_lines)
    fig_w = max((len(l) for l in fig_lines), default=10)

    # ── TOP BAR: figlet left, badges + eye right ──────────────────────────────
    hline("╔", "═", "╗")

    badge   = "[OFFLINE]"
    tagline = "watching. locally."
    eye     = "◣_◢"
    mid_row = fig_h // 2

    for i, fl in enumerate(fig_lines):
        t = RT()
        t.append(fl.ljust(fig_w), style="bold white")
        if i == mid_row:
            t.append("   ")
            t.append(badge,   style="bold green")
            t.append("  " + tagline, style="dim white")
            # right-align eye
            used = fig_w + 3 + len(badge) + 2 + len(tagline)
            t.append(" " * max(0, IW - used - len(eye) - 3))
            t.append(eye, style="dim white")
        brow(t)

    hline()

    # ── Hardware + Dog side by side ───────────────────────────────────────────
    _, tier_label = hardware.score_system(hw)

    # Build hardware rows as plain-text tuples (label, Rich Text value)
    hw_rows: list[tuple[str, RT]] = []

    def hw_add(label: str, val: RT):
        hw_rows.append((label, val))

    v = RT(hw["cpu_name"], style="white")
    v.append(f"  {hw['cpu_cores']}C/{hw['cpu_threads']}T", style="dim")
    hw_add("CPU", v)

    v = RT(f"{hw['ram_total_gb']} GB", style="white")
    v.append(f"  {hw['ram_free_gb']} GB free", style="dim")
    hw_add("RAM", v)

    for g in hw["gpus"]:
        v = RT(g["name"], style="white")
        if g["vram_mb"] > 0:
            v.append(f"  {g['vram_mb']} MB VRAM", style="dim")
        hw_add("GPU", v)

    if npu:
        v = RT(npu["name"], style="green")
        if npu.get("tops"):
            v.append(f"  {npu['tops']} TOPS", style="dim")
        hw_add("NPU", v)

    v = RT("SSD/NVMe" if hw["ssd"] else "HDD", style="white")
    v.append(f"  {hw['disk_free_gb']} GB free", style="dim")
    hw_add("Disk", v)
    hw_add("OS",   RT(hw["os"], style="white"))
    hw_add("Tier", RT(tier_label, style="white"))

    # Build dog rows (32 cols × 16 rows)
    small    = [row[::2] for row in DOGE_CHARS[::2]]
    dog_rows: list[RT] = []
    for drow in small:
        t = RT()
        for ch in drow:
            t.append(" " if ch == "@" else ch,
                     style="" if ch == "@" else _lurk_color(ch))
        dog_rows.append(t)

    dog_w  = max(len(dr.plain) for dr in dog_rows)
    L_COL  = max(60, IW - dog_w - 8)   # left column width
    total  = max(len(hw_rows) + 2, len(dog_rows))

    blank()

    for i in range(total):
        # Left side
        if i == 0:
            left = RT("── SYSTEM HARDWARE ", style=f"bold {C_PRIMARY}")
            left.append("─" * max(0, L_COL - 22), style="dim")
        elif 1 <= i <= len(hw_rows):
            label, val_rt = hw_rows[i - 1]
            left = RT(f"{label:<8}", style="dim")
            left.append_text(val_rt)
        else:
            left = RT("")

        # Right side (dog, vertically centred)
        dog_offset = max(0, (total - len(dog_rows)) // 2)
        di         = i - dog_offset
        right      = dog_rows[di] if 0 <= di < len(dog_rows) else RT("")

        t = RT()
        t.append_text(left)
        t.append(" " * max(0, L_COL - len(left.plain) + 4))
        t.append_text(right)
        brow(t)

    blank()
    hline()

    # ── Meme ─────────────────────────────────────────────────────────────────
    blank()
    meme = random.choice(MEMES)
    pad  = max(0, (IW - len(meme)) // 2)
    m    = RT(" " * pad + meme, style="yellow")
    brow(m)
    blank()
    hline("╚", "═", "╝")
    console.print()


# ─── Hardware Scan ─────────────────────────────────────────────────────────────

def run_hardware_scan() -> dict:
    with console.status(f"[{C_PRIMARY}]Scanning hardware...[/]", spinner="dots"):
        hw = hardware.detect()
    return hw


# ─── Model Selection (Rich — used at startup and for /model) ──────────────────

def show_model_menu(hw: dict) -> dict | None:
    recs = models.recommend(hw)
    local = models.get_local_models()
    local_files = {m["file"] for m in local}

    console.print(Panel(
        f"[bold {C_PRIMARY}]Model Selection[/]  [{C_DIM}]system: {hw['ram_total_gb']}GB RAM  "
        f"{hw['primary_gpu']['name'] if hw['primary_gpu'] else 'CPU only'}[/]",
        border_style=C_PRIMARY, padding=(0, 1)
    ))
    console.print()

    idx = 1

    if local:
        console.print(f"[bold {C_ACCENT}]Installed[/]")
        for m in local:
            console.print(f"  [{C_PRIMARY}]{idx}[/]  [bold]{m['name']}[/]  [{C_DIM}]{m['size_gb']} GB  installed[/]")
            idx += 1
        console.print()

    console.print(f"[bold {C_ACCENT}]Recommended for your system[/]")
    unique_recs = [m for m in recs if m["file"] not in local_files]
    for m in unique_recs:
        tags = "  ".join(f"[{C_DIM}]{t}[/]" for t in m["tags"][:3])
        console.print(f"  [{C_PRIMARY}]{idx}[/]  [bold]{m['name']}[/]  [{C_DIM}]{m['size_gb']} GB[/]  {tags}")
        console.print(f"      [{C_DIM}]{m['desc']}[/]")
        idx += 1
    console.print()

    all_models = local + unique_recs
    console.print(f"  [{C_DIM}]a[/]  Browse all models")
    console.print(f"  [{C_DIM}]q[/]  Back / Quit")
    console.print()

    choice = Prompt.ask(f"[bold {C_PRIMARY}]>[/]")

    if choice.lower() == "q":
        return None
    if choice.lower() == "a":
        return browse_all_models(hw)
    try:
        n = int(choice) - 1
        if 0 <= n < len(all_models):
            return all_models[n]
    except ValueError:
        pass
    console.print(f"[{C_DIM}]Invalid choice.[/]")
    return show_model_menu(hw)


def browse_all_models(hw: dict) -> dict | None:
    local_files = {m["file"] for m in models.get_local_models()}
    console.print()
    console.print(Panel(f"[bold {C_PRIMARY}]All Models[/]", border_style=C_PRIMARY, padding=(0, 1)))
    console.print()
    for i, m in enumerate(models.REGISTRY):
        installed = m["file"] in local_files
        viable    = m["min_ram_gb"] <= hw["ram_total_gb"]
        status    = f"[{C_DIM}]installed[/]" if installed else f"[{C_DIM}]{m['size_gb']} GB[/]"
        warn      = f"  [{C_DIM}]needs {m['min_ram_gb']}GB RAM[/]" if not viable else ""
        tags      = "  ".join(f"[{C_DIM}]{t}[/]" for t in m["tags"][:3])
        console.print(f"  [{C_PRIMARY}]{i+1:2}[/]  [bold]{m['name']}[/]  {status}{warn}  {tags}")
        console.print(f"       [{C_DIM}]{m['desc']}[/]")
    console.print()
    console.print(f"  [{C_DIM}]b[/]  Back   [{C_DIM}]q[/]  Quit")
    console.print()
    choice = Prompt.ask(f"[bold {C_PRIMARY}]>[/]")
    if choice.lower() == "b":
        return show_model_menu(hw)
    if choice.lower() == "q":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models.REGISTRY):
            return models.REGISTRY[idx]
    except ValueError:
        pass
    return browse_all_models(hw)


# ─── Download Flow ─────────────────────────────────────────────────────────────

def ensure_model_downloaded(model: dict) -> str | None:
    dest = models.MODELS_DIR / model["file"]
    if dest.exists():
        return str(dest)

    file_key = model.get("file") or model.get("filename")
    model_id = model.get("id")
    if not model_id:
        m = next((x for x in models.REGISTRY if x["file"] == file_key), None)
        if not m:
            console.print(f"[{C_ERROR}]Cannot find model in registry.[/]")
            return None
        model_id = m["id"]

    console.print()
    console.print(Panel(
        f"[bold]Download {model['name']}[/]\n"
        f"[{C_DIM}]Size: ~{model.get('size_gb', '?')} GB  ·  Saved to: {models.MODELS_DIR}[/]",
        border_style=C_WARN, padding=(0, 1)
    ))

    choice = Prompt.ask(
        f"[{C_ACCENT}]Download now?[/] [{C_DIM}](y/n)[/]",
        choices=["y", "n"], default="y"
    )
    if choice == "n":
        console.print(f"[{C_DIM}]Skipping download.[/]")
        return None

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(bar_width=40, style=C_PRIMARY, complete_style=C_SUCCESS),
        "[progress.percentage]{task.percentage:>3.0f}%",
        DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
        console=console,
    ) as progress:
        size_bytes = int(model.get("size_gb", 1) * 1024**3)
        task = progress.add_task(f"[{C_PRIMARY}]Downloading {model['name']}...", total=size_bytes)

        def on_progress(downloaded, total):
            progress.update(task, completed=downloaded, total=total)

        try:
            path = models.download_model(model_id, on_progress)
            progress.update(task, completed=size_bytes)
            console.print(f"[{C_SUCCESS}]✓ Downloaded to {path}[/]")
            return str(path)
        except Exception as e:
            console.print(f"\n[{C_ERROR}]Download failed: {e}[/]")
            return None


# ─── Server Bootstrap ──────────────────────────────────────────────────────────

def ensure_server_binary() -> bool:
    if server._server_exe().exists():
        return True

    console.print()
    console.print(Panel(
        f"[bold {C_WARN}]llama-server not found[/]\n"
        f"[{C_DIM}]Lurk needs the llama.cpp server binary to run AI models locally.[/]",
        border_style=C_WARN, padding=(0, 1)
    ))

    choice = Prompt.ask(
        f"[{C_ACCENT}]Download llama-server now? (~10 MB)[/] [{C_DIM}](y/n)[/]",
        choices=["y", "n"], default="y"
    )
    if choice == "n":
        console.print(f"[{C_DIM}]Cannot run models without llama-server. Exiting.[/]")
        return False

    status_text = [""]
    done = threading.Event()

    def do_download():
        def cb(msg): status_text[0] = msg
        server.download_server(status_cb=cb)
        done.set()

    threading.Thread(target=do_download, daemon=True).start()

    with Live(console=console, refresh_per_second=4) as live:
        while not done.is_set():
            live.update(Text(f"  {status_text[0]}", style=C_PRIMARY))
            time.sleep(0.25)

    if server._server_exe().exists():
        console.print(f"[{C_SUCCESS}]✓ llama-server ready[/]")
        return True
    else:
        console.print(f"[{C_ERROR}]Failed to download llama-server.[/]")
        return False


def load_model(model_path: str, model_name: str, hw: dict, ctx: int = 4096) -> bool:
    if not Path(model_path).exists():
        console.print(f"[{C_ERROR}]Model file not found: {model_path}[/]")
        return False

    gpu_layers = 99 if (hw["has_nvidia"] or hw.get("has_amd_gpu")) else 0
    logs       = []
    last_log   = [""]
    spinner_frames = ["|", "/", "-", "\\"]

    def log_cb(line):
        logs.append(line)
        last_log[0] = line

    started = threading.Event()
    success = [False]

    def start_server():
        success[0] = server.start(model_path, gpu_layers=gpu_layers, ctx=ctx, log_cb=log_cb)
        started.set()

    threading.Thread(target=start_server, daemon=True).start()

    console.print()
    i = 0
    while not started.is_set():
        frame = spinner_frames[i % len(spinner_frames)]
        console.print(f"  [{C_PRIMARY}]{frame}[/] [{C_DIM}]Loading {model_name}...[/]", end="\r")
        time.sleep(0.15)
        i += 1
    console.print()

    if success[0]:
        console.print(f"[{C_SUCCESS}]✓ {model_name} loaded[/]  [{C_DIM}]gpu_layers={gpu_layers}  ctx={ctx}[/]")
        return True
    else:
        console.print(f"[{C_ERROR}]Failed to load model.[/]")
        error_lines = [l for l in logs if any(x in l.lower() for x in (
            "error", "failed", "fatal", "assert", "ggml", "cudaerror", "out of memory", "alloc"
        ))]
        shown = error_lines[-8:] if error_lines else logs[-8:]
        for line in shown:
            console.print(f"  [{C_DIM}]{line}[/]")
        return False


# ─── Chat Loop — prompt_toolkit split-pane ────────────────────────────────────

def chat_loop(model_name: str, hw: dict, npu: dict | None = None, loaded_learnings: list[str] | None = None) -> str:
    """Full-screen split-pane chat. Returns 'quit', 'switch', or 'restart'."""
    import learnings as LRN
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.layout.containers import VSplit, HSplit, Window, ConditionalContainer
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import FormattedText

    class _ChatWindow(Window):
        """Window subclass whose scroll isn't cursor-driven (display-only content)."""
        def _scroll_when_linewrapping(self, ui_content, width, height):
            self.horizontal_scroll = 0
            self.vertical_scroll_2 = 0
            if ui_content.line_count == 0:
                self.vertical_scroll = 0
                return
            # Walk backwards from the last logical line to find the topmost line
            # that still fills the window (no blank space at bottom).
            prev, used = ui_content.line_count - 1, 0
            for ln in range(ui_content.line_count - 1, -1, -1):
                used += ui_content.get_height_for_line(ln, width, self.get_line_prefix)
                if used > height:
                    topmost = prev
                    break
                prev = ln
            else:
                topmost = 0
            self.vertical_scroll = max(0, min(self.vertical_scroll, topmost))

    # ── Style constants (black + purple only) ─────────────────────────────────
    S_USER   = "bold fg:ansiwhite"
    S_AI     = "fg:ansiwhite"
    S_DIM    = "fg:ansigray"
    S_CMD    = "bold fg:#8b5cf6"
    S_ERR    = "fg:#8b5cf6"
    S_PURPLE = "fg:#8b5cf6"
    S_HEADER = "bold fg:#8b5cf6"
    S_BORDER = "fg:ansigray"
    S_POPUP  = "bg:#1a0030 fg:#e0e0e0"

    # ── Shared state ──────────────────────────────────────────────────────────
    history:       list = []
    result:        list = ["quit"]
    app_ref:       list = [None]
    streaming:     list = [False]
    current_model: list = [model_name]

    # ── Learnings context ─────────────────────────────────────────────────────
    _loaded_names: list[str] = list(loaded_learnings or [])
    _learning_ctx: list[str] = [LRN.build_context(_loaded_names)]

    # ── Teach mode ────────────────────────────────────────────────────────────
    _teach_mode:    list = [False]
    _teach_name:    list = ["untitled"]
    _teach_lines:   list = []   # user messages collected during teach session

    chat_frags: list = [
        (S_DIM,  f"  Lurk  ·  {model_name}\n"),
        (S_DIM,  "  Type / to see commands  ·  Ctrl+C to quit\n\n"),
    ]
    if _loaded_names:
        chat_frags.append((S_DIM, f"  Loaded: {', '.join(_loaded_names)}\n\n"))

    # Scroll: True = auto-follow bottom; False = user is scrolling history
    _follow_scroll: list = [True]

    def append(style: str, text: str) -> None:
        chat_frags.append((style, text))
        if app_ref[0]:
            if _follow_scroll[0]:
                chat_win.vertical_scroll = 999999
            app_ref[0].invalidate()

    # ── Bar helper — purple only, no traffic-light colors ────────────────────
    def _bar(pct: float, w: int = 10) -> list:
        filled = round(min(max(pct, 0), 100) / 100 * w)
        return [(S_PURPLE, "█" * filled), (S_DIM, "░" * (w - filled))]

    # ── Stats + model sidebar ─────────────────────────────────────────────────
    _stats: dict = {}

    def get_sidebar_ft() -> FormattedText:
        s = _stats
        frags: list = []
        def a(st, tx): frags.append((st, tx))

        a(S_HEADER, "  LURK  ")
        a(S_BORDER, "│  ")

        name = current_model[0]
        if len(name) > 16: name = name[:14] + ".."
        a(S_DIM, f"{name}  ")
        a(S_BORDER, "│  ")

        cpu = s.get("cpu_pct", 0)
        a(S_DIM, "CPU "); frags.extend(_bar(cpu, 8)); a(S_DIM, f" {cpu:3.0f}%   ")

        ram_pct   = s.get("ram_pct", 0)
        ram_used  = s.get("ram_used_gb", 0)
        ram_total = s.get("ram_total_gb", 0)
        a(S_DIM, "RAM "); frags.extend(_bar(ram_pct, 8)); a(S_DIM, f" {ram_used:.1f}/{ram_total:.0f}GB   ")

        if "gpu_pct" in s:
            gpu_pct    = s["gpu_pct"]
            temp       = s.get("gpu_temp")
            vram_used  = s.get("gpu_vram_used_mb", 0) / 1024
            vram_total = max(s.get("gpu_vram_total_mb", 1), 1) / 1024
            vram_pct   = vram_used / vram_total * 100
            a(S_DIM, "GPU "); frags.extend(_bar(gpu_pct, 8))
            a(S_DIM, f" {gpu_pct:3d}%" + (f" {temp}°C" if temp else "") + "   ")
            a(S_DIM, "VRAM "); frags.extend(_bar(vram_pct, 8))
            a(S_DIM, f" {vram_used:.1f}/{vram_total:.0f}GB   ")

        if npu:
            a(S_PURPLE, "NPU ✓")

        return FormattedText(frags)

    stats_win = Window(
        content=FormattedTextControl(get_sidebar_ft, focusable=False),
        height=1,
        dont_extend_height=True,
    )

    # ── Chat output window ────────────────────────────────────────────────────
    chat_win = _ChatWindow(
        content=FormattedTextControl(
            lambda: FormattedText(chat_frags),
            focusable=False,
        ),
        wrap_lines=True,
        always_hide_cursor=True,
    )

    # Intercept native scroll so mouse wheel manages follow mode
    _orig_scroll_up = chat_win._scroll_up
    def _chat_scroll_up():
        _follow_scroll[0] = False
        _orig_scroll_up()
        if app_ref[0]:
            app_ref[0].invalidate()
    chat_win._scroll_up = _chat_scroll_up

    _orig_scroll_down = chat_win._scroll_down
    def _chat_scroll_down():
        before = chat_win.vertical_scroll
        _orig_scroll_down()
        # If position didn't change, we're at the bottom — re-enable follow
        if chat_win.vertical_scroll == before:
            _follow_scroll[0] = True
            chat_win.vertical_scroll = 999999
        if app_ref[0]:
            app_ref[0].invalidate()
    chat_win._scroll_down = _chat_scroll_down

    # ── Input line ────────────────────────────────────────────────────────────
    input_buf = Buffer(name="input", multiline=False)
    def _input_prefix(*_):
        if _teach_mode[0]:
            return [("bold fg:#f59e0b", f"  TEACH({_teach_name[0]}) > ")]
        return [(S_CMD, "  > ")]

    input_win = Window(
        content=BufferControl(buffer=input_buf, focusable=True),
        height=1,
        get_line_prefix=_input_prefix,
    )

    # ── Left sidebar: LURK logo + dog art (static, built once) ──────────────
    SIDEBAR_W = 36
    _sidebar_frags: list = []

    # LURK figlet — pick largest font that fits in SIDEBAR_W-2
    _lurk_fig: list[str] = []
    for _font in ["standard", "small", "banner"]:
        try:
            _raw = pyfiglet.figlet_format("LURK", font=_font)
            _lines = _raw.splitlines()
            if _lines and max((len(l) for l in _lines), default=0) <= SIDEBAR_W - 2:
                _lurk_fig = _lines
                break
        except Exception:
            continue
    if not _lurk_fig:
        _lurk_fig = ["  LURK"]

    # helper: centre a plain string in the sidebar
    def _sc(text: str, style: str) -> None:
        pad = max(0, (SIDEBAR_W - len(text)) // 2)
        _sidebar_frags.append((style, " " * pad + text + "\n"))

    _sidebar_frags.append((S_BORDER, "─" * SIDEBAR_W + "\n"))

    # LURK figlet — centre whole block by max line width
    _fig_w   = max((len(l) for l in _lurk_fig), default=6)
    _fig_pad = max(0, (SIDEBAR_W - _fig_w) // 2)
    for _fl in _lurk_fig:
        _sidebar_frags.append((S_HEADER, " " * _fig_pad + _fl + "\n"))

    _sidebar_frags.append((S_BORDER, "─" * SIDEBAR_W + "\n"))
    _sidebar_frags.append(("", "\n"))

    # Dog art (32 cols × 16 rows) — centred
    _small_dog = [r[::2] for r in DOGE_CHARS[::2]]
    _dog_w     = max(len(r.rstrip()) for r in _small_dog)
    for _drow in _small_dog:
        _stripped = _drow.rstrip("@").rstrip()   # remove trailing bg chars
        _pad = max(0, (SIDEBAR_W - max(_dog_w, len(_stripped))) // 2)
        _sidebar_frags.append(("", " " * _pad))
        for _ch in _drow:
            if _ch == "@":
                _sidebar_frags.append(("", " "))
            else:
                _sidebar_frags.append((_lurk_color(_ch), _ch))
        _sidebar_frags.append(("", "\n"))

    _sidebar_frags.append(("", "\n"))
    _sidebar_frags.append((S_BORDER, "─" * SIDEBAR_W + "\n"))
    _sidebar_frags.append(("", "\n"))

    # System specs under the dog
    _, _tier = hardware.score_system(hw)
    _specs = [
        ("CPU", hw["cpu_name"].split(" w/")[0].strip()),
        ("   ", f"{hw['cpu_cores']}C / {hw['cpu_threads']}T"),
        ("RAM", f"{hw['ram_total_gb']} GB"),
    ]
    for _g in hw.get("gpus", []):
        if _g["vram_mb"] > 0:
            _short = _g["name"].replace("NVIDIA ", "").replace("AMD ", "")
            _specs.append(("GPU", _short[:SIDEBAR_W - 6]))
    if npu:
        _specs.append(("NPU", npu["name"].replace("AMD ", "")))
    _specs.append(("OS ", hw["os"].replace("Windows ", "Win ")))
    _specs.append(("   ", _tier))

    for _label, _val in _specs:
        _line = f"{_label}  {_val}"
        if len(_line) > SIDEBAR_W - 2:
            _line = _line[:SIDEBAR_W - 3] + "…"
        _sidebar_frags.append((S_DIM, f" {_label}  "))
        _sidebar_frags.append(("fg:ansiwhite", f"{_val[:SIDEBAR_W - len(_label) - 4]}\n"))

    _sidebar_frags.append(("", "\n"))
    _sidebar_frags.append((S_BORDER, "─" * SIDEBAR_W + "\n"))
    _sidebar_frags.append(("", "\n"))
    _sidebar_frags.append((S_HEADER, "  COMMANDS\n"))
    _sidebar_frags.append(("", "\n"))
    for _cmd, _cdesc in [
        ("/model",     "switch model"),
        ("/clear",     "clear history"),
        ("/teach",     "start teaching"),
        ("/done",      "save & end teach"),
        ("/learnings", "manage"),
        ("/exit",      "quit"),
    ]:
        _sidebar_frags.append((S_PURPLE, f"  {_cmd:<10}"))
        _sidebar_frags.append((S_DIM,    f"  {_cdesc}\n"))
    _sidebar_frags.append(("", "\n"))
    _sidebar_frags.append((S_BORDER, "─" * SIDEBAR_W + "\n"))

    sidebar_win = Window(
        content=FormattedTextControl(lambda: FormattedText(_sidebar_frags), focusable=False),
        width=SIDEBAR_W,
        dont_extend_width=True,
        style="bg:#000000",
    )

    # ── Commands (shown inline below input when "/" is typed) ────────────────
    CMDS = [
        ("/model",     "switch model"),
        ("/clear",     "clear history"),
        ("/teach",     "start teaching"),
        ("/done",      "save + end teach"),
        ("/learnings", "manage learnings"),
        ("/restart",   "reload model"),
        ("/help",      "show help"),
        ("/exit",      "quit"),
    ]


    def get_hints_ft() -> FormattedText:
        frags: list = []
        for cmd, desc in CMDS:
            frags.append((S_CMD,    f"  {cmd}"))
            frags.append((S_DIM,    f" {desc}"))
            frags.append((S_BORDER, "   "))
        return FormattedText(frags)

    hints_visible = Condition(lambda: input_buf.text.startswith("/"))

    hints_win = ConditionalContainer(
        content=Window(
            content=FormattedTextControl(get_hints_ft, focusable=False),
            height=1,
            dont_extend_height=True,
        ),
        filter=hints_visible,
    )

    # ── Layout: sidebar left │ chat + input + stats right ───────────────────
    layout = Layout(
        VSplit([
            sidebar_win,
            Window(width=1, char="│", style=S_BORDER),
            HSplit([
                chat_win,
                Window(height=1, char="─", style=S_BORDER),
                input_win,
                hints_win,
                Window(height=1, char="─", style=S_BORDER),
                stats_win,
            ]),
        ]),
        focused_element=input_win,
    )

    # ── Keybindings ───────────────────────────────────────────────────────────
    kb = KeyBindings()

    @kb.add("enter")
    def _enter(event):
        if streaming[0]:
            return
        raw = input_buf.text.strip()
        if not raw:
            return
        input_buf.reset()
        cmd = raw.lower()

        if cmd in ("/exit", "/quit"):
            result[0] = "quit"; event.app.exit(); return

        if cmd == "/model":
            result[0] = "switch"; event.app.exit(); return

        if cmd == "/restart":
            result[0] = "restart"; event.app.exit(); return

        if cmd == "/clear":
            chat_frags.clear()
            chat_frags.append((S_DIM, "  History cleared.\n\n"))
            history.clear()
            event.app.invalidate()
            return

        if cmd == "/help":
            append(S_HEADER, "\n  Commands\n")
            for c, d in CMDS:
                append(S_CMD, f"  {c:<10}")
                append(S_DIM, f"  {d}\n")
            append("", "\n")
            return

        # /teach [name] — enter teaching mode
        if cmd.startswith("/teach"):
            if _teach_mode[0]:
                append(S_DIM, "  Already in teach mode. Type /done to save and exit.\n\n")
                return
            name = raw[6:].strip() or "untitled"
            _teach_mode[0]  = True
            _teach_name[0]  = name
            _teach_lines.clear()
            append(S_HEADER, f"\n  Teaching mode: {name}\n")
            append(S_DIM,    "  Type everything you want to teach. /done to save and exit.\n\n")
            event.app.invalidate()
            return

        # /done — end teaching session, ask AI to summarize, save
        if cmd == "/done":
            if not _teach_mode[0]:
                append(S_DIM, "  Not in teach mode.\n\n")
                return
            if not _teach_lines:
                _teach_mode[0] = False
                append(S_DIM, "  Teach session ended (nothing to save).\n\n")
                event.app.invalidate()
                return
            _teach_mode[0] = False
            name = _teach_name[0]
            raw_knowledge = "\n".join(_teach_lines)
            append(S_DIM, f"\n  Saving learning '{name}'...\n")
            streaming[0] = True
            append(S_AI, "  ")

            def _save_teaching():
                try:
                    summary_prompt = (
                        f"The user just taught you the following during a teaching session called '{name}'.\n\n"
                        f"{raw_knowledge}\n\n"
                        "Write clean, structured notes summarizing all of this. "
                        "Use headings and bullet points. Include every specific fact, rule, or preference mentioned. "
                        "Write it as reference material to be loaded in future conversations."
                    )
                    def on_tok(t): append(S_AI, t)
                    summary = inference.stream_chat(
                        [{"role": "user", "content": summary_prompt}],
                        base_url=server.base_url(),
                        on_token=on_tok,
                    )
                    append("", "\n\n")
                    saved_path = LRN.save(name, summary)
                    # Add to loaded context for this session
                    if name not in _loaded_names:
                        _loaded_names.append(name)
                        _learning_ctx[0] = LRN.build_context(_loaded_names)
                    append(S_DIM, f"  Saved to {saved_path.name}. Active in this session.\n\n")
                except Exception as e:
                    append(S_ERR, f"\n  Error saving: {e}\n\n")
                finally:
                    streaming[0] = False

            threading.Thread(target=_save_teaching, daemon=True).start()
            return

        # /learnings — list, load, or delete learnings
        if cmd.startswith("/learnings"):
            all_files = LRN.list_all()
            if not all_files:
                append(S_DIM, "\n  No saved learnings yet. Use /teach to create one.\n\n")
                return
            sub = raw[10:].strip()
            if sub.startswith("load "):
                lname = sub[5:].strip()
                if lname not in _loaded_names:
                    _loaded_names.append(lname)
                    _learning_ctx[0] = LRN.build_context(_loaded_names)
                    append(S_DIM, f"\n  Loaded '{lname}' into this session.\n\n")
                else:
                    append(S_DIM, f"\n  '{lname}' is already loaded.\n\n")
                return
            if sub.startswith("unload "):
                lname = sub[7:].strip()
                if lname in _loaded_names:
                    _loaded_names.remove(lname)
                    _learning_ctx[0] = LRN.build_context(_loaded_names)
                    append(S_DIM, f"\n  Unloaded '{lname}'.\n\n")
                return
            if sub.startswith("delete "):
                lname = sub[7:].strip()
                LRN.delete(lname)
                if lname in _loaded_names:
                    _loaded_names.remove(lname)
                    _learning_ctx[0] = LRN.build_context(_loaded_names)
                append(S_DIM, f"\n  Deleted '{lname}'.\n\n")
                return
            # Default: list all
            append(S_HEADER, "\n  Saved Learnings\n")
            for f in all_files:
                sz   = f.stat().st_size
                stem = f.stem
                mark = " [loaded]" if stem in _loaded_names else ""
                append(S_PURPLE, f"  {stem:<24}")
                append(S_DIM,    f"  {sz//1024}KB{mark}\n")
            append(S_DIM, "\n  /learnings load <name>   /learnings delete <name>\n\n")
            return

        # Regular message → inference in background thread
        # If in teach mode, collect this line and use a teaching system prompt
        if _teach_mode[0]:
            _teach_lines.append(raw)

        append(S_USER, f"  > {raw}\n\n")
        history.append({"role": "user", "content": raw})
        streaming[0] = True
        append(S_AI, "  ")

        _teach_ctx_now = (
            f"The user is currently teaching you about '{_teach_name[0]}'. "
            "Listen carefully, ask clarifying questions if something is unclear, "
            "and confirm what you've understood. Do not make up or add information "
            "beyond what the user tells you."
            if _teach_mode[0] else ""
        )
        _extra = (_learning_ctx[0] + ("\n\n" + _teach_ctx_now if _teach_ctx_now else "")).strip()

        def run_inference(extra=_extra):
            try:
                def on_token(t: str):
                    append(S_AI, t)

                def on_tool_call(name: str, args: dict):
                    arg_str = "  ".join(f"{k}={str(v)[:40]}" for k, v in args.items())
                    append(S_DIM, f"\n  ▶ {name}  {arg_str}\n")

                def on_tool_result(name: str, res: str):
                    append(S_DIM, f"  └─ {len(res.strip().splitlines())} lines\n\n")
                    append(S_AI, "  ")

                final = inference.stream_chat(
                    history.copy(),
                    base_url=server.base_url(),
                    on_token=on_token,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                    extra_context=extra,
                )
                append("", "\n\n")
                history.append({"role": "assistant", "content": final})
            except Exception as e:
                append(S_ERR, f"\n  Error: {e}\n\n")
                if history and history[-1]["role"] == "user":
                    history.pop()
            finally:
                streaming[0] = False

        threading.Thread(target=run_inference, daemon=True).start()

    @kb.add("pageup")
    def _pageup(event):
        import shutil
        page = max(shutil.get_terminal_size((80, 30)).lines - 4, 8)
        _follow_scroll[0] = False
        chat_win.vertical_scroll = max(0, chat_win.vertical_scroll - page)
        event.app.invalidate()

    @kb.add("pagedown")
    def _pagedown(event):
        import shutil
        page = max(shutil.get_terminal_size((80, 30)).lines - 4, 8)
        ri = getattr(chat_win, "render_info", None)
        if ri:
            max_scroll = max(0, ri.content_height - ri.window_height)
            chat_win.vertical_scroll = min(chat_win.vertical_scroll + page, max_scroll)
            if chat_win.vertical_scroll >= max_scroll - 2:
                _follow_scroll[0] = True
                chat_win.vertical_scroll = 999999
        else:
            chat_win.vertical_scroll = 999999
            _follow_scroll[0] = True
        event.app.invalidate()

    @kb.add("end")
    @kb.add("c-end")
    def _scroll_to_bottom(event):
        _follow_scroll[0] = True
        chat_win.vertical_scroll = 999999
        event.app.invalidate()

    @kb.add("home")
    @kb.add("c-home")
    def _scroll_to_top(event):
        _follow_scroll[0] = False
        chat_win.vertical_scroll = 0
        event.app.invalidate()

    @kb.add("c-c")
    def _ctrl_c(event):
        result[0] = "quit"
        event.app.exit()

    # ── Application ───────────────────────────────────────────────────────────
    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        mouse_support=True,
        style=Style.from_dict({"": "bg:#000000 fg:#e0e0e0"}),
    )
    app_ref[0] = app

    # Background: update stats every 0.5 s and trigger a redraw
    def _stats_loop():
        psutil.cpu_percent(interval=None)  # prime the counter (first call returns 0)
        while True:
            try:
                new = hardware.get_live_stats()
                _stats.update(new)
            except Exception:
                pass
            time.sleep(0.5)
            try:
                if app_ref[0]:
                    app_ref[0].invalidate()
                else:
                    break
            except Exception:
                break

    threading.Thread(target=_stats_loop, daemon=True).start()

    app.run()
    app_ref[0] = None
    return result[0]


# ─── Entry Point ───────────────────────────────────────────────────────────────

_DEFAULT_MODEL_ID = "qwen2.5-7b-q4"


def _select_learnings() -> list[str]:
    """Show a numbered list of saved learnings; user picks which to load. Returns names."""
    import learnings as LRN
    all_files = LRN.list_all()
    if not all_files:
        return []

    console.print()
    console.rule(f"[{C_PRIMARY}]Learnings[/]", style=C_DIM)
    for i, f in enumerate(all_files, 1):
        sz   = f.stat().st_size
        mark = f"[{C_DIM}]{sz // 1024}KB[/]"
        console.print(f"  [{C_PRIMARY}]{i}[/]  {f.stem:<30} {mark}")
    console.print()
    console.print(f"  [{C_DIM}]Load which? Numbers separated by spaces, 'all', or Enter to skip:[/]")

    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return []

    if not raw:
        return []
    if raw.lower() == "all":
        return [f.stem for f in all_files]

    selected = []
    for tok in raw.split():
        try:
            idx = int(tok) - 1
            if 0 <= idx < len(all_files):
                selected.append(all_files[idx].stem)
        except ValueError:
            # Treat as a name directly
            if any(f.stem == tok for f in all_files):
                selected.append(tok)
    return selected


def main():
    console.clear()
    hw  = run_hardware_scan()
    npu = hardware.detect_npu()

    loaded_learnings = _select_learnings()

    cfg = models.load_config()

    if not ensure_server_binary():
        sys.exit(1)

    # Start with last explicitly-chosen model, otherwise always Qwen 2.5
    saved_id = cfg.get("chosen_model")   # only set when user picks via /model
    selected = (
        next((m for m in models.REGISTRY if m["id"] == saved_id), None)
        if saved_id else None
    ) or next(m for m in models.REGISTRY if m["id"] == _DEFAULT_MODEL_ID)

    model_path: str | None = None
    ctx: int = 4096

    while True:
        if model_path is None:
            model_path = ensure_model_downloaded(selected)
            if not model_path:
                console.print(f"[{C_DIM}]Pick a different model.[/]")
                picked = show_model_menu(hw)
                if picked is None:
                    console.print(f"[{C_DIM}]Goodbye.[/]")
                    sys.exit(0)
                selected = picked
                continue

            cfg["chosen_model"] = selected.get("id") or selected.get("file")
            models.save_config(cfg)
            meta = next((m for m in models.REGISTRY if m["id"] == selected.get("id")), {})
            ctx  = min(meta.get("ctx", selected.get("ctx", 4096)), 16384)

        if not load_model(model_path, selected["name"], hw, ctx=ctx):
            console.print(f"[{C_DIM}]Pick a different model.[/]")
            picked = show_model_menu(hw)
            if picked is None:
                console.print(f"[{C_DIM}]Goodbye.[/]")
                sys.exit(0)
            selected    = picked
            model_path  = None
            continue

        try:
            action = chat_loop(selected["name"], hw, npu=npu, loaded_learnings=loaded_learnings)
        finally:
            server.stop()

        if action == "quit":
            break
        elif action == "restart":
            pass  # keep selected + model_path, reload same model
        else:
            # /model command — show Rich picker, then restart with new model
            console.clear()
            picked = show_model_menu(hw)
            if picked is None:
                console.print(f"[{C_DIM}]Goodbye.[/]")
                break
            selected   = picked
            model_path = None

    console.print(f"[{C_DIM}]Goodbye.[/]")


if __name__ == "__main__":
    main()

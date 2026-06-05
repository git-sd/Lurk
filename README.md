```
                    ██╗      ██╗   ██╗██████╗ ██╗  ██╗
                    ██║      ██║   ██║██╔══██╗██║ ██╔╝
                    ██║      ██║   ██║██████╔╝█████╔╝
                    ██║      ██║   ██║██╔══██╗██╔═██╗
                    ███████╗ ╚██████╔╝██║  ██║██║  ██╗
                    ╚══════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
```

```
          / \      _
      ___/   \____/ \        such local
     /               \         very offline
    |    ^       ^    |           wow AI
    |       ___       |
     \     (   )     /
      \     ---     /
       `--_______--'
      /             \
     / |           | \
    /  |           |  \
        \         /
         |       |
        /|       |\
```

---

**Lurk** is a fullscreen, fully offline AI assistant that runs directly in your terminal. No cloud. No filters. No bullshit.

Built by [Shreyan Das](https://github.com/Shreyan11)

---

## Features

- **Fully offline** — powered by llama.cpp, everything runs on your machine
- **Fullscreen TUI** — split-pane terminal UI with live hardware stats, ASCII doge, and scrollable chat
- **No filter** — seriously, none
- **Tool use** — reads/writes files, runs shell commands
- **Teach mode** — `/teach` to teach it stuff, saved as persistent learnings loaded on startup
- **Fan control** — spins your fans when the AI is generating, cools down when done
- **Model switching** — swap between models mid-session with `/model`
- **Live stats bar** — CPU, RAM, GPU, VRAM, NPU all live at the bottom

---

## Install

**Requirements:** Python 3.10+, Windows (Linux/Mac mostly works too)

```bash
git clone https://github.com/Shreyan11/lurk
cd lurk
pip install -e .
lurk
```

Or just run directly:

```bash
python lurk.py
```

---

## Commands

| Command | What it does |
|---|---|
| `/model` | Switch the active model |
| `/teach <name>` | Start a teaching session — tell it stuff, it remembers |
| `/done` | End teach session and save as a learning |
| `/learnings` | List all saved learnings |
| `/learnings load <name>` | Load a learning into this session |
| `/learnings delete <name>` | Delete a saved learning |
| `/fans` | Show fan control status |
| `/fans set <on_cmd> \| <off_cmd>` | Set custom fan commands |
| `/fans test` | Test fan spin for 3 seconds |
| `/clear` | Clear chat history |
| `/restart` | Reload the model |
| `/help` | Show all commands |
| `/exit` | Quit |

---

## Models

Lurk auto-downloads models on first run. Defaults to **Qwen 2.5 7B Q4**.

| Model | Size | Good for |
|---|---|---|
| Qwen 2.5 7B Q4 | 4.5 GB | Coding, reasoning, general use |
| DeepSeek R1 8B Q4 | 5.2 GB | Deep reasoning, thinking problems |
| Phi-4 14B Q4 | 8.5 GB | Long context, nuanced tasks |
| Llama 3.1 8B Q4 | 4.9 GB | Fast, general purpose |

Models are stored in `~/LURK/models/`.

---

## Teach Mode

```
/teach python
> I use snake_case for everything
> my projects live in C:/dev/
> I hate type hints but I use them anyway
/done
```

Next time you open Lurk, select that learning at the prompt and it loads the notes into context. The AI will know your preferences without you repeating yourself.

---

## Fan Control

By default, Lurk forces your CPU to 100% minimum frequency while the AI generates — more heat, fans spin up, back to normal when it's done. No extra software needed.

If you have dedicated fan control software:
```
/fans set <spin_up_command> | <cool_down_command>
```

---

## Data

Everything lives in `~/LURK/`:

```
~/LURK/
  models/        downloaded GGUF model files
  learnings/     your saved teaching sessions (.md files)
  config.json    active model, fan commands, settings
```

---

*by Shreyan Das*

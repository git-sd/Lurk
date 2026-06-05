```
                     ##                      #####              
                  ###  #                   ##     #             
                 #0xxX# #                ##  #XXX# #            
               # #00ooO# #####          #  #0xxoox###           
               # #0Oo*=O#      ########  #0xxxxxx=O #           
               ###0xxo*=xX#####        #XOxxxoooxoo#            
           ####  XxxxOOxxxxxxxOOOO00XXXOooxxooooxxo# #          
         ##    #XOO0000Oxxxxxxxxxxxxxooooxxx==*=xxo# #          
        #  #XX000000000xxxxxxxxxxxxxxxooxxxo=**ox=x##           
       # #X0000000O000xxxxxxOOxxxxxxxxxxxxo**=xxooX #           
      # #0O0000OxOxOOxxxxxO0000OxxxxxxxxxxxooxxxxxO# #          
      ##X0XX00=,.;xxxxxxxO00000Oxxxxxxxxxxxxxxxxxxxx# #         
     # XX###XO*  :xxxxxOxx00xxo+=xxxxxxxxxxxxxxxxxxxO##         
      ######0OOxoOxOOO0Oxxx+OO,  ;xxxOOO0OxxOOxxxxxxxX #        
      ######XXXXX000000xxxo+xO;:+oxxX#########XOxxxxx0##        
     ######Xx==oox00000O00xxoxxxOOX############XOxxxxO #        
    ######0.   .  ,0#XXX000XXXXX################Oxxxxx# #       
    ######X;   .  ,O ###X0X#####################OxxxxxO##       
    #####0=*,..:+*x#####00X#####################0xxxxxxX #      
    #####Xx==**===x####000X#########XXXXXXXXXXXOxxxxxxxO #      
    #######o++;++*xXXX000O0XXXXXXXXXXXXXXXXXXXXxxxxxxxxOX##     
     #####X0OOxxoo==ooxOOO00XXXXXXXXX000XXXXX0xxxxxoxxxx0# #    
     ######X000XXXX00000XX0XXXXXXXX00XXXXXXXX0xxxooxxxxx0X#     
      #XXX0000000000XXXXXXXXXXXXX0000XXXXXX0xxxoooxxxxxx0X      
     # X000000000000XXXXXXXXX000000XXXXXXXXOOxooooxxxxx0X0# #   
    # #X000000000000000XXXXX000000XX0XXXXXXOxooooxxxOO000xO #   
    # #XXX000000000000000000000000XXXXXXXXXX0oooxxx0XX0XOox# #  
     #XXXXX000OOOOOOOOOOOOOOO0000XXXXXXXXXX0xxxO00X000X0ooo# #  
   # #XXXXXXX000OOOOOOOOOO00000000000000000000XXXXXX00XOoooX #  
   # #XXXXXXXXX00000OOOO00000000000000000000XXXXXXXXX0XOooo0 #  
    #XXXXXXXXXXX0000OOO0000000000000000000XXXXXXXXXXX0xooooO #  
  # #XXXXXXXXXXXXX0X000X000000000000000XXXXXXXXXXXXXOxooxxo0 #  
```

```
  ██╗      ██╗   ██╗██████╗ ██╗  ██╗
  ██║      ██║   ██║██╔══██╗██║ ██╔╝
  ██║      ██║   ██║██████╔╝█████╔╝
  ██║      ██║   ██║██╔══██╗██╔═██╗
  ███████╗ ╚██████╔╝██║  ██║██║  ██╗
  ╚══════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
```

**Fully offline AI assistant that runs in your terminal. No cloud. No filters. No bullshit.**

Built by [Shreyan Das](https://github.com/git-sd)

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

**Requirements:** Python 3.10+, Windows

```bash
git clone https://github.com/git-sd/Lurk
cd Lurk
pip install -e .
lurk
```

Or run directly:

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

Next time you open Lurk, select that learning at the prompt and it loads into context automatically.

---

## Fan Control

By default, Lurk forces your CPU to 100% minimum frequency while the AI generates — more heat, fans spin up, back to normal when done. No extra software needed.

To use dedicated fan control software instead:
```
/fans set <spin_up_command> | <cool_down_command>
/fans test
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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the game

```bash
python3 dungeon.py
```

Requires a terminal that supports `curses` and Unicode block characters (any modern Linux/macOS terminal). Minimum recommended size: 90×26.

## Architecture

The entire game lives in `dungeon.py` as a single-file curses application. The flow is:

```
curses.wrapper(main)
  └── splash_screen()          # title / key-wait
  └── loop:
        run_level()            # one dungeon floor
          ├── generate_dungeon()   # BSP room + L-corridor map
          ├── place_entities()     # player, enemies, items, stairs
          └── game loop (real-time):
                compute_fov()      # Bresenham line-of-sight
                render()           # map + side panel + message log
                move_enemies()     # timer-driven AI
                handle input       # move / attack / collect / descend
        game_over_screen()     # win or death
```

**Key design points:**

- **Turn model is hybrid**: player moves on keypress; enemies move on a 0.35 s timer (`stdscr.nodelay(True)`). This gives real-time feel without tick-rate coupling.
- **FOV** is a simple radius sweep with Bresenham occlusion. `seen` is a persistent set so explored-but-dark tiles remain visible (dimmed with color pair `C_DARK`).
- **Gear bonuses** (`atk_bonus`, `def_bonus`) accumulate across levels and are passed into each `run_level()` call, then applied on top of the base `Entity` stats.
- **Particles** (`Particle` dataclass) are time-to-live overlays rendered before terrain/entities each frame and pruned by `time.time()`.
- **Color pairs** are module-level constants (`C_WALL`, `C_PLAYER`, …) initialized once in `init_colors()`.

## Adding content

- **New enemy type**: add a tuple to `enemy_types` inside `place_entities()` — `(symbol, name, hp, max_hp, attack, color_pair)`.
- **New item kind**: add a branch in the item pickup block inside `run_level()` and a definition in `item_defs` inside `place_entities()`.
- **More levels**: change the `gs.level > 5` win condition in `main()`.

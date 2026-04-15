# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the game

```bash
python3 dungeon.py
```

Requires a terminal that supports `curses` and Unicode block characters (any modern Linux/macOS terminal). Minimum recommended size: 90×26.

## Architecture

`dungeon.py` is the entry point; all game logic lives in the `dungeon/` package.

```
dungeon.py                  # thin entry point: curses.wrapper(main)
dungeon/
  __init__.py               # re-exports main
  constants.py              # color pair IDs, MAP_H/W, DIRECTIONS
  entities.py               # Entity, Item, Particle, GameState dataclasses
  mapgen.py                 # generate_dungeon(), place_entities()
  fov.py                    # compute_fov()
  ai.py                     # move_enemies()
  render.py                 # draw_bar(), render(), splash_screen(), game_over_screen()
  game.py                   # init_colors(), run_level(), main()
```

Call flow:

```
curses.wrapper(main)          # game.py
  └── splash_screen()         # render.py — title / key-wait
  └── loop:
        run_level()           # game.py — one dungeon floor
          ├── generate_dungeon()   # mapgen.py — BSP room + L-corridor map
          ├── place_entities()     # mapgen.py — player, enemies, items, stairs
          └── game loop (real-time):
                compute_fov()      # fov.py — Bresenham line-of-sight
                render()           # render.py — map + side panel + message log
                move_enemies()     # ai.py — timer-driven AI
                handle input       # game.py — move / attack / collect / descend
        game_over_screen()    # render.py — win or death
```

**Key design points:**

- **Turn model is hybrid**: player moves on keypress; enemies move on a 0.35 s timer (`stdscr.nodelay(True)`). This gives real-time feel without tick-rate coupling.
- **FOV** is a simple radius sweep with Bresenham occlusion. `seen` is a persistent set so explored-but-dark tiles remain visible (dimmed with color pair `C_DARK`).
- **Gear bonuses** (`atk_bonus`, `def_bonus`) accumulate across levels and are passed into each `run_level()` call, then applied on top of the base `Entity` stats.
- **Particles** (`Particle` dataclass) are time-to-live overlays rendered before terrain/entities each frame and pruned by `time.time()`.
- **Color pairs** are module-level constants (`C_WALL`, `C_PLAYER`, …) defined in `constants.py` and initialized once in `init_colors()`.

## Adding content

- **New enemy type**: add a tuple to `enemy_types` inside `place_entities()` in `dungeon/mapgen.py` — `(symbol, name, hp, max_hp, attack, color_pair)`.
- **New item kind**: add a branch in the item pickup block inside `run_level()` in `dungeon/game.py` and a definition in `item_defs` inside `place_entities()` in `dungeon/mapgen.py`.
- **More levels**: change the `gs.level > 5` win condition in `main()` in `dungeon/game.py`.

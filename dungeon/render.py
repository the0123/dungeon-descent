import curses
import time

from .constants import (
    MAP_H, MAP_W,
    C_WALL, C_FLOOR, C_PLAYER, C_STAIRS, C_UI, C_BLOOD, C_ITEM, C_GOLD, C_DARK,
)
from .entities import GameState


def draw_bar(win, r, c, current, maximum, width, full_col, empty_col, label):
    filled = int(width * current / max(1, maximum))
    win.addstr(r, c, label, curses.color_pair(C_UI) | curses.A_BOLD)
    llen = len(label)
    for i in range(width):
        col_pair = full_col if i < filled else empty_col
        win.addstr(r, c + llen + i, '█', curses.color_pair(col_pair))
    win.addstr(r, c + llen + width, f' {current}/{maximum}', curses.color_pair(C_UI))


def render(stdscr, grid, player, enemies, items, visible, seen, gs: GameState,
           stair_pos, atk_bonus, def_bonus):
    h, w = stdscr.getmaxyx()
    stdscr.erase()

    map_off_r = 0
    map_off_c = 0
    now = time.time()

    # Active particles for quick lookup
    particle_cells = {}
    gs.particles = [p for p in gs.particles if now - p.born < p.ttl]
    for p in gs.particles:
        particle_cells[(p.row, p.col)] = p

    for r in range(MAP_H):
        for c in range(MAP_W):
            sr = map_off_r + r
            sc = map_off_c + c
            if sr >= h - 1 or sc >= w:
                continue
            cell = grid[r][c]
            in_fov  = (r, c) in visible
            in_seen = (r, c) in seen

            if not in_fov and not in_seen:
                continue

            if not in_fov:
                stdscr.addstr(sr, sc, cell, curses.color_pair(C_DARK))
                continue

            # Particle overlay
            if (r, c) in particle_cells:
                p = particle_cells[(r, c)]
                stdscr.addstr(sr, sc, p.symbol, curses.color_pair(p.color) | curses.A_BOLD)
                continue

            # Player
            if r == player.row and c == player.col:
                stdscr.addstr(sr, sc, player.symbol,
                              curses.color_pair(C_PLAYER) | curses.A_BOLD)
                continue

            # Enemies
            drawn = False
            for e in enemies:
                if e.alive and e.row == r and e.col == c:
                    stdscr.addstr(sr, sc, e.symbol,
                                  curses.color_pair(e.color) | curses.A_BOLD)
                    drawn = True
                    break
            if drawn:
                continue

            # Items
            drawn = False
            for it in items:
                if not it.collected and it.row == r and it.col == c:
                    stdscr.addstr(sr, sc, it.symbol,
                                  curses.color_pair(it.color) | curses.A_BOLD)
                    drawn = True
                    break
            if drawn:
                continue

            # Stairs
            if (r, c) == stair_pos:
                stdscr.addstr(sr, sc, '>', curses.color_pair(C_STAIRS) | curses.A_BOLD)
                continue

            # Terrain
            if cell == '#':
                stdscr.addstr(sr, sc, '▓', curses.color_pair(C_WALL))
            elif cell == '.':
                stdscr.addstr(sr, sc, '·', curses.color_pair(C_FLOOR))

    # ── Side panel ────────────────────────────────────────────────────────────
    px = MAP_W + 2
    if px + 22 < w:
        attrs = curses.color_pair(C_UI) | curses.A_BOLD
        stdscr.addstr(0,  px, '╔══ DUNGEON DESCENT ══╗', attrs)
        stdscr.addstr(1,  px, f'║  Level  : {gs.level:<11}║', attrs)
        stdscr.addstr(2,  px, f'║  Score  : {gs.score:<11}║', attrs)
        stdscr.addstr(3,  px, f'║  Gold   : {gs.gold:<11}║', attrs)
        stdscr.addstr(4,  px, f'║  Turns  : {gs.turns:<11}║', attrs)
        stdscr.addstr(5,  px, f'║  ATK +{atk_bonus}  DEF +{def_bonus}     ║', attrs)
        stdscr.addstr(6,  px, '╠═══════════════════════╣', attrs)
        stdscr.addstr(7,  px, f'║ HP {player.hp:>3}/{player.max_hp:<3}           ║', attrs)
        hp_pct = player.hp / player.max_hp
        bar_w = 18
        filled = int(bar_w * hp_pct)
        hp_col = C_ITEM if hp_pct > 0.5 else (C_GOLD if hp_pct > 0.25 else C_BLOOD)
        bar = '█' * filled + '░' * (bar_w - filled)
        stdscr.addstr(8,  px, f'║ {bar} ║', curses.color_pair(hp_col) | curses.A_BOLD)
        stdscr.addstr(9,  px, '╠═══════════════════════╣', attrs)
        stdscr.addstr(10, px, '║ CONTROLS              ║', attrs)
        stdscr.addstr(11, px, '║ WASD/↑↓←→ Move        ║', attrs)
        stdscr.addstr(12, px, '║ > Enter stairs        ║', attrs)
        stdscr.addstr(13, px, '║ Q Quit  R Restart     ║', attrs)
        stdscr.addstr(14, px, '╠═══════════════════════╣', attrs)
        stdscr.addstr(15, px, '║ LEGEND                ║', attrs)
        stdscr.addstr(16, px, '║ @ You  r Rat          ║', attrs)
        stdscr.addstr(17, px, '║ g Gob  o Orc  D Dragon║', attrs)
        stdscr.addstr(18, px, '║ ! Pot  $ Gold         ║', attrs)
        stdscr.addstr(19, px, '║ / Sword ] Shield      ║', attrs)
        stdscr.addstr(20, px, '║ > Stairs to next lvl  ║', attrs)
        stdscr.addstr(21, px, '╚═══════════════════════╝', attrs)

    # ── Message log ───────────────────────────────────────────────────────────
    msg_row = MAP_H
    msgs = gs.messages[-3:]
    for i, msg in enumerate(msgs):
        if msg_row + i < h - 1:
            stdscr.addstr(msg_row + i, 0, msg[:w-1], curses.color_pair(C_UI))

    stdscr.refresh()


def splash_screen(stdscr):
    h, w = stdscr.getmaxyx()
    lines = [
        "  ██████╗ ██╗   ██╗███╗   ██╗ ██████╗ ███████╗ ██████╗ ███╗   ██╗",
        "  ██╔══██╗██║   ██║████╗  ██║██╔════╝ ██╔════╝██╔═══██╗████╗  ██║",
        "  ██║  ██║██║   ██║██╔██╗ ██║██║  ███╗█████╗  ██║   ██║██╔██╗ ██║",
        "  ██║  ██║██║   ██║██║╚██╗██║██║   ██║██╔══╝  ██║   ██║██║╚██╗██║",
        "  ██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝███████╗╚██████╔╝██║ ╚████║",
        "  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝",
        "",
        "              D  E  S  C  E  N  T",
        "",
        "         Descend into the dungeon, claim the gold,",
        "          defeat the beasts, reach the Dragon lair.",
        "",
        "           WASD / Arrow Keys  —  Move & Attack",
        "           Walk onto >         —  Next Level",
        "           Walk onto items     —  Auto collect",
        "",
        "                Press ENTER to begin",
        "                  Q to quit",
    ]
    stdscr.erase()
    start_r = max(0, h//2 - len(lines)//2)
    for i, line in enumerate(lines):
        r = start_r + i
        if r >= h:
            break
        sc = max(0, w//2 - len(line)//2)
        try:
            stdscr.addstr(r, sc, line, curses.color_pair(C_PLAYER) | curses.A_BOLD)
        except curses.error:
            pass
    stdscr.refresh()
    while True:
        k = stdscr.getkey()
        if k in ('\n', '\r', 'KEY_ENTER'):
            return True
        if k in ('q', 'Q'):
            return False


def game_over_screen(stdscr, gs: GameState, won=False):
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    lines = (
        ["YOU WIN! The Dragon is slain!",
         f"Score: {gs.score}   Gold: {gs.gold}   Turns: {gs.turns}",
         "Press R to play again or Q to quit"]
        if won else
        ["YOU DIED",
         f"Level {gs.level}  Score: {gs.score}  Gold: {gs.gold}  Turns: {gs.turns}",
         "Press R to play again or Q to quit"]
    )
    col = C_ITEM if won else C_BLOOD
    for i, line in enumerate(lines):
        r = h//2 - 1 + i
        sc = max(0, w//2 - len(line)//2)
        try:
            stdscr.addstr(r, sc, line, curses.color_pair(col) | curses.A_BOLD)
        except curses.error:
            pass
    stdscr.refresh()
    while True:
        k = stdscr.getkey()
        if k in ('r', 'R'):
            return True
        if k in ('q', 'Q'):
            return False

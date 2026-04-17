import curses
import time

from .constants import (
    MAP_H, MAP_W,
    C_WALL, C_FLOOR, C_PLAYER, C_STAIRS, C_UI, C_BLOOD, C_ITEM, C_GOLD, C_DARK,
)
from .entities import GameState

# Width (in columns) of the right-side panel, including its 2-column gap from the map.
_PANEL_COLS = 25   # 2 gap + 23 panel content


def draw_bar(win, r, c, current, maximum, width, full_col, empty_col, label):
    filled = int(width * current / max(1, maximum))
    win.addstr(r, c, label, curses.color_pair(C_UI) | curses.A_BOLD)
    llen = len(label)
    for i in range(width):
        col_pair = full_col if i < filled else empty_col
        win.addstr(r, c + llen + i, '█', curses.color_pair(col_pair))
    win.addstr(r, c + llen + width, f' {current}/{maximum}', curses.color_pair(C_UI))


def _s(stdscr, r, c, text, attr=0):
    """addstr that silently ignores out-of-bounds writes."""
    try:
        stdscr.addstr(r, c, text, attr)
    except curses.error:
        pass


def _hp_color(pct):
    if pct > 0.5:
        return C_ITEM
    if pct > 0.25:
        return C_GOLD
    return C_BLOOD


def render(stdscr, grid, player, enemies, items, visible, seen, gs: GameState,
           stair_pos, atk_bonus, def_bonus):
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    now = time.time()

    gs.particles = [p for p in gs.particles if now - p.born < p.ttl]
    pcells = {(p.row, p.col): p for p in gs.particles}

    # ── Responsive layout ────────────────────────────────────────────────
    # Right panel needs MAP_W + gap + panel = 60 + 2 + 23 = 85 cols minimum.
    show_right  = w >= MAP_W + _PANEL_COLS
    status_rows = 0 if show_right else 2   # compact 2-line bar when narrow

    # Viewport: as much map as will fit without overlapping UI.
    vp_h = min(MAP_H, max(3, h - status_rows - 3))
    vp_w = min(MAP_W, max(10, w - (_PANEL_COLS if show_right else 0)))

    # Camera: keep player centred, clamped to map edges.
    cam_r = max(0, min(MAP_H - vp_h, player.row - vp_h // 2))
    cam_c = max(0, min(MAP_W - vp_w, player.col - vp_w // 2))

    # ── Map (through viewport) ───────────────────────────────────────────
    for vr in range(vp_h):
        for vc in range(vp_w):
            r, c   = cam_r + vr, cam_c + vc
            sr, sc = vr, vc
            if sr >= h - 1 or sc >= w:
                continue

            cell    = grid[r][c]
            in_fov  = (r, c) in visible
            in_seen = (r, c) in seen

            if not in_fov and not in_seen:
                continue

            if not in_fov:
                _s(stdscr, sr, sc, cell, curses.color_pair(C_DARK))
                continue

            if (r, c) in pcells:
                p = pcells[(r, c)]
                _s(stdscr, sr, sc, p.symbol,
                   curses.color_pair(p.color) | curses.A_BOLD)
                continue

            if r == player.row and c == player.col:
                _s(stdscr, sr, sc, player.symbol,
                   curses.color_pair(C_PLAYER) | curses.A_BOLD)
                continue

            drawn = False
            for e in enemies:
                if e.alive and e.row == r and e.col == c:
                    _s(stdscr, sr, sc, e.symbol,
                       curses.color_pair(e.color) | curses.A_BOLD)
                    drawn = True
                    break
            if drawn:
                continue

            for it in items:
                if not it.collected and it.row == r and it.col == c:
                    _s(stdscr, sr, sc, it.symbol,
                       curses.color_pair(it.color) | curses.A_BOLD)
                    drawn = True
                    break
            if drawn:
                continue

            if (r, c) == stair_pos:
                _s(stdscr, sr, sc, '>', curses.color_pair(C_STAIRS) | curses.A_BOLD)
                continue

            if cell == '#':
                _s(stdscr, sr, sc, '▓', curses.color_pair(C_WALL))
            elif cell == '.':
                _s(stdscr, sr, sc, '·', curses.color_pair(C_FLOOR))

    # ── Right side panel (wide screens) ──────────────────────────────────
    if show_right:
        px    = MAP_W + 2
        bold  = curses.color_pair(C_UI) | curses.A_BOLD

        def ps(row, text, a=None):
            if row < h - 1:
                _s(stdscr, row, px, text, bold if a is None else a)

        ps(0,  '╔══ DUNGEON DESCENT ══╗')
        ps(1,  f'║  Level  : {gs.level:<11}║')
        ps(2,  f'║  Score  : {gs.score:<11}║')
        ps(3,  f'║  Gold   : {gs.gold:<11}║')
        ps(4,  f'║  Turns  : {gs.turns:<11}║')
        ps(5,  f'║  ATK +{atk_bonus}  DEF +{def_bonus}     ║')
        ps(6,  '╠═══════════════════════╣')
        ps(7,  f'║ HP {player.hp:>3}/{player.max_hp:<3}           ║')
        hp_pct = player.hp / max(1, player.max_hp)
        bar_w  = 18
        filled = int(bar_w * hp_pct)
        hp_col = _hp_color(hp_pct)
        bar    = '█' * filled + '░' * (bar_w - filled)
        ps(8,  f'║ {bar} ║', curses.color_pair(hp_col) | curses.A_BOLD)
        ps(9,  '╠═══════════════════════╣')
        ps(10, '║ CONTROLS              ║')
        ps(11, '║ WASD/↑↓←→ Move        ║')
        ps(12, '║ > Enter stairs        ║')
        ps(13, '║ Q Quit  R Restart     ║')
        ps(14, '╠═══════════════════════╣')
        ps(15, '║ LEGEND                ║')
        ps(16, '║ @ You  r Rat          ║')
        ps(17, '║ g Gob  o Orc  D Dragon║')
        ps(18, '║ ! Pot  $ Gold         ║')
        ps(19, '║ / Sword ] Shield      ║')
        ps(20, '║ > Stairs to next lvl  ║')
        ps(21, '╚═══════════════════════╝')

    # ── Compact status bar (narrow screens) ──────────────────────────────
    else:
        hp_pct = player.hp / max(1, player.max_hp)
        hp_col = _hp_color(hp_pct)
        bar_w  = max(4, min(12, w // 5))
        filled = int(bar_w * hp_pct)
        bar    = '█' * filled + '░' * (bar_w - filled)
        bold   = curses.color_pair(C_UI) | curses.A_BOLD

        row1 = vp_h
        if row1 < h - 1:
            prefix = ' HP:'
            try:
                stdscr.addstr(row1, 0, prefix, bold)
                col = len(prefix)
                stdscr.addstr(row1, col, bar[:filled],
                              curses.color_pair(hp_col) | curses.A_BOLD)
                stdscr.addstr(row1, col + filled, bar[filled:],
                              curses.color_pair(C_DARK) | curses.A_BOLD)
                stats = (f' {player.hp}/{player.max_hp}'
                         f'  Lv:{gs.level}  $:{gs.gold}  Sc:{gs.score}')
                stdscr.addstr(row1, col + bar_w,
                              stats[:w - col - bar_w - 1],
                              curses.color_pair(C_UI))
            except curses.error:
                pass

        row2 = vp_h + 1
        if row2 < h - 1:
            hint = (f' ATK+{atk_bonus} DEF+{def_bonus}'
                    f'  WASD:move  >:stairs  Q:quit')
            _s(stdscr, row2, 0, hint[:w - 1], curses.color_pair(C_UI))

    # ── Message log ───────────────────────────────────────────────────────
    msg_start = vp_h + status_rows
    for i, msg in enumerate(gs.messages[-3:]):
        row = msg_start + i
        if row < h - 1:
            _s(stdscr, row, 0, msg[:w - 1], curses.color_pair(C_UI))

    stdscr.refresh()


def splash_screen(stdscr):
    h, w = stdscr.getmaxyx()
    stdscr.erase()

    art = [
        "  ██████╗ ██╗   ██╗███╗   ██╗ ██████╗ ███████╗ ██████╗ ███╗   ██╗",
        "  ██╔══██╗██║   ██║████╗  ██║██╔════╝ ██╔════╝██╔═══██╗████╗  ██║",
        "  ██║  ██║██║   ██║██╔██╗ ██║██║  ███╗█████╗  ██║   ██║██╔██╗ ██║",
        "  ██║  ██║██║   ██║██║╚██╗██║██║   ██║██╔══╝  ██║   ██║██║╚██╗██║",
        "  ██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝███████╗╚██████╔╝██║ ╚████║",
        "  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝",
    ]
    art_w = max(len(line) for line in art)

    if w >= art_w:
        lines = art + [
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
    else:
        lines = [
            "DUNGEON DESCENT",
            "",
            "Descend. Defeat beasts. Reach the Dragon.",
            "",
            "WASD / Arrows  —  Move & Attack",
            "Walk onto >    —  Next Level",
            "Walk onto items — Auto collect",
            "",
            "ENTER to begin    Q to quit",
        ]

    start_r = max(0, h // 2 - len(lines) // 2)
    for i, line in enumerate(lines):
        r = start_r + i
        if r >= h:
            break
        sc = max(0, w // 2 - len(line) // 2)
        _s(stdscr, r, sc, line, curses.color_pair(C_PLAYER) | curses.A_BOLD)

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
        r = h // 2 - 1 + i
        if r >= h:
            break
        sc = max(0, w // 2 - len(line) // 2)
        _s(stdscr, r, sc, line, curses.color_pair(col) | curses.A_BOLD)
    stdscr.refresh()
    while True:
        k = stdscr.getkey()
        if k in ('r', 'R'):
            return True
        if k in ('q', 'Q'):
            return False

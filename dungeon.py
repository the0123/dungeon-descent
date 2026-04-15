#!/usr/bin/env python3
"""
DUNGEON DESCENT - A Roguelike Console Game
Controls: WASD or Arrow Keys to move, Q to quit, R to restart
"""

import curses
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ── Palette ──────────────────────────────────────────────────────────────────
C_NORMAL   = 0
C_WALL     = 1
C_FLOOR    = 2
C_PLAYER   = 3
C_ENEMY    = 4
C_ITEM     = 5
C_STAIRS   = 6
C_UI       = 7
C_BLOOD    = 8
C_GOLD     = 9
C_DARK     = 10

DIRECTIONS = {'w': (-1, 0), 's': (1, 0), 'a': (0, -1), 'd': (0, 1),
              'KEY_UP': (-1, 0), 'KEY_DOWN': (1, 0), 'KEY_LEFT': (0, -1), 'KEY_RIGHT': (0, 1)}

# ── Data classes ─────────────────────────────────────────────────────────────
@dataclass
class Entity:
    row: int
    col: int
    symbol: str
    name: str
    hp: int
    max_hp: int
    attack: int
    color: int
    alive: bool = True

@dataclass
class Item:
    row: int
    col: int
    kind: str   # 'potion' | 'gold' | 'sword' | 'shield'
    value: int
    symbol: str
    color: int
    collected: bool = False

@dataclass
class Particle:
    row: int
    col: int
    symbol: str
    color: int
    ttl: float          # time-to-live in seconds
    born: float = field(default_factory=time.time)

@dataclass
class GameState:
    level: int = 1
    score: int = 0
    gold: int = 0
    messages: List[str] = field(default_factory=list)
    particles: List[Particle] = field(default_factory=list)
    turns: int = 0

# ── Map generation ────────────────────────────────────────────────────────────
MAP_H = 22
MAP_W = 60

def generate_dungeon(level: int):
    """BSP-ish room-and-corridor dungeon."""
    grid = [['#'] * MAP_W for _ in range(MAP_H)]
    rooms: List[Tuple[int,int,int,int]] = []   # (r, c, h, w)

    attempts = 40 + level * 5
    for _ in range(attempts):
        rh = random.randint(4, 9)
        rw = random.randint(6, 14)
        r  = random.randint(1, MAP_H - rh - 1)
        c  = random.randint(1, MAP_W - rw - 1)
        # Check no overlap (with 1-cell border)
        overlap = any(
            r < er + eh + 1 and r + rh + 1 > er and
            c < ec + ew + 1 and c + rw + 1 > ec
            for er, ec, eh, ew in rooms
        )
        if not overlap:
            rooms.append((r, c, rh, rw))
            for dr in range(rh):
                for dc in range(rw):
                    grid[r + dr][c + dc] = '.'

    # Connect rooms with L-shaped corridors
    random.shuffle(rooms)
    for i in range(1, len(rooms)):
        r1, c1, h1, w1 = rooms[i-1]
        r2, c2, h2, w2 = rooms[i]
        mid1r = r1 + h1 // 2
        mid1c = c1 + w1 // 2
        mid2r = r2 + h2 // 2
        mid2c = c2 + w2 // 2
        # Horizontal then vertical
        for cc in range(min(mid1c, mid2c), max(mid1c, mid2c) + 1):
            grid[mid1r][cc] = '.'
        for rr in range(min(mid1r, mid2r), max(mid1r, mid2r) + 1):
            grid[rr][mid2c] = '.'

    return grid, rooms

def place_entities(grid, rooms, level, gs: GameState):
    if not rooms:
        return None, [], []

    # Player in first room
    pr, pc, ph, pw = rooms[0]
    player = Entity(
        row=pr + ph//2, col=pc + pw//2,
        symbol='@', name='Hero',
        hp=20 + (level-1)*2, max_hp=20 + (level-1)*2,
        attack=3 + level, color=C_PLAYER
    )

    # Stairs in last room
    lr, lc, lh, lw = rooms[-1]
    stair_pos = (lr + lh//2, lc + lw//2)
    grid[stair_pos[0]][stair_pos[1]] = '>'

    # Enemies
    enemy_types = [
        ('r', 'Rat',    4+level,  4+level,  1+level//2,  C_ENEMY),
        ('g', 'Goblin', 6+level*2, 6+level*2, 2+level,   C_ENEMY),
        ('o', 'Orc',   10+level*3,10+level*3, 3+level,   C_BLOOD),
        ('D', 'Dragon',20+level*5,20+level*5, 5+level*2, C_BLOOD),
    ]
    enemies: List[Entity] = []
    n_enemies = 3 + level * 2
    for room in rooms[1:]:
        rr, rc, rh, rw = room
        n = random.randint(0, 3)
        for _ in range(n):
            if len(enemies) >= n_enemies:
                break
            sym, name, hp, mhp, atk, col = random.choice(
                enemy_types[:min(level, len(enemy_types))]
            )
            er = rr + random.randint(0, rh-1)
            ec = rc + random.randint(0, rw-1)
            if grid[er][ec] == '.' and (er, ec) != stair_pos:
                enemies.append(Entity(er, ec, sym, name, hp, mhp, atk, col))

    # Items
    items: List[Item] = []
    item_defs = [
        ('potion', '!', C_ITEM,  8),
        ('gold',   '$', C_GOLD,  random.randint(5, 20)),
        ('sword',  '/', C_ITEM,  2),
        ('shield', ']', C_ITEM,  1),
    ]
    n_items = 4 + level
    placed = 0
    for room in rooms:
        if placed >= n_items:
            break
        rr, rc, rh, rw = room
        if random.random() < 0.7:
            kind, sym, col, val = random.choice(item_defs)
            ir = rr + random.randint(0, rh-1)
            ic = rc + random.randint(0, rw-1)
            if grid[ir][ic] == '.':
                items.append(Item(ir, ic, kind, val, sym, col))
                placed += 1

    return player, enemies, items, stair_pos

# ── FOV (simple radius) ───────────────────────────────────────────────────────
def compute_fov(grid, pr, pc, radius=7):
    visible = set()
    for dr in range(-radius, radius+1):
        for dc in range(-radius, radius+1):
            if dr*dr + dc*dc > radius*radius:
                continue
            r, c = pr + dr, pc + dc
            if 0 <= r < MAP_H and 0 <= c < MAP_W:
                # Bresenham line from player to cell
                blocked = False
                steps = max(abs(dr), abs(dc))
                if steps == 0:
                    visible.add((r, c))
                    continue
                for s in range(1, steps):
                    ir = round(pr + dr * s / steps)
                    ic = round(pc + dc * s / steps)
                    if grid[ir][ic] == '#':
                        blocked = True
                        break
                if not blocked:
                    visible.add((r, c))
    return visible

# ── Enemy AI ──────────────────────────────────────────────────────────────────
def move_enemies(enemies, player, grid, visible, gs: GameState):
    occupied = {(player.row, player.col)}
    for e in enemies:
        if e.alive:
            occupied.add((e.row, e.col))

    for e in enemies:
        if not e.alive:
            continue
        if (e.row, e.col) not in visible:
            # Random wander
            if random.random() < 0.3:
                dr, dc = random.choice([(-1,0),(1,0),(0,-1),(0,1)])
                nr, nc = e.row+dr, e.col+dc
                if grid[nr][nc] != '#' and (nr,nc) not in occupied:
                    occupied.discard((e.row, e.col))
                    e.row, e.col = nr, nc
                    occupied.add((e.row, e.col))
            continue

        dr = player.row - e.row
        dc = player.col - e.col
        dist = abs(dr) + abs(dc)

        if dist == 1 and dr*dc == 0:
            # Attack player
            dmg = max(0, e.attack - random.randint(0, 1))
            player.hp -= dmg
            gs.messages.append(f"{e.name} hits you for {dmg}!")
            gs.particles.append(Particle(player.row, player.col, '*', C_BLOOD, 0.4))
        else:
            # Chase
            steps = [(dr,0) if dr!=0 else None, (0,dc) if dc!=0 else None]
            random.shuffle(steps)
            for step in steps:
                if step is None:
                    continue
                sr, sc = step
                nr, nc = e.row+sr, e.col+sc
                if grid[nr][nc] != '#' and (nr,nc) not in occupied:
                    occupied.discard((e.row, e.col))
                    e.row, e.col = nr, nc
                    occupied.add((e.row, e.col))
                    break

# ── Drawing ───────────────────────────────────────────────────────────────────
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

    # ── Map area ──────────────────────────────────────────────────────────────
    map_off_r = 0
    map_off_c = 0
    now = time.time()

    # Active particles dict for quick lookup
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
                # Dim explored cells
                if cell == '#':
                    stdscr.addstr(sr, sc, cell, curses.color_pair(C_DARK))
                else:
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

    # ── Side panel (right of map) ─────────────────────────────────────────────
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
        # HP bar
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

    # ── Message log (bottom) ──────────────────────────────────────────────────
    msg_row = MAP_H
    msgs = gs.messages[-3:]
    for i, msg in enumerate(msgs):
        if msg_row + i < h - 1:
            stdscr.addstr(msg_row + i, 0, msg[:w-1], curses.color_pair(C_UI))

    stdscr.refresh()

# ── Splash & death screens ────────────────────────────────────────────────────
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

# ── Main game loop ────────────────────────────────────────────────────────────
def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_WALL,   curses.COLOR_BLUE,    -1)
    curses.init_pair(C_FLOOR,  curses.COLOR_WHITE,   -1)
    curses.init_pair(C_PLAYER, curses.COLOR_GREEN,   -1)
    curses.init_pair(C_ENEMY,  curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_ITEM,   curses.COLOR_CYAN,    -1)
    curses.init_pair(C_STAIRS, curses.COLOR_MAGENTA, -1)
    curses.init_pair(C_UI,     curses.COLOR_WHITE,   -1)
    curses.init_pair(C_BLOOD,  curses.COLOR_RED,     -1)
    curses.init_pair(C_GOLD,   curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_DARK,   8,                    -1)   # dark gray

def run_level(stdscr, gs: GameState, atk_bonus: int, def_bonus: int):
    """Run one dungeon level. Returns ('next', atk, def) | ('dead',) | ('quit',)."""
    grid, rooms = generate_dungeon(gs.level)
    result = place_entities(grid, rooms, gs.level, gs)
    if result[0] is None:
        return ('next', atk_bonus, def_bonus)   # degenerate map, skip
    player, enemies, items, stair_pos = result

    # Apply bonuses from previous levels
    player.attack  += atk_bonus
    player.max_hp  += def_bonus * 2
    player.hp       = player.max_hp

    seen: set = set()
    gs.messages.append(f'Welcome to level {gs.level}! Find the stairs (>).')

    stdscr.nodelay(True)
    last_enemy_move = time.time()

    while True:
        visible = compute_fov(grid, player.row, player.col)
        seen |= visible

        render(stdscr, grid, player, enemies, items, visible, seen, gs,
               stair_pos, atk_bonus, def_bonus)

        # Enemies move on a timer (not per keypress) for fluid feel
        now = time.time()
        if now - last_enemy_move > 0.35:
            move_enemies(enemies, player, grid, visible, gs)
            last_enemy_move = now
            if player.hp <= 0:
                player.alive = False

        if not player.alive:
            return ('dead',)

        # Input
        try:
            key = stdscr.getkey()
        except curses.error:
            time.sleep(0.03)
            continue

        if key in ('q', 'Q'):
            return ('quit',)

        move_dir = None
        if key in DIRECTIONS:
            move_dir = DIRECTIONS[key]
        elif key == 'w': move_dir = (-1, 0)
        elif key == 's': move_dir = ( 1, 0)
        elif key == 'a': move_dir = ( 0,-1)
        elif key == 'd': move_dir = ( 0, 1)

        if move_dir is None:
            continue

        gs.turns += 1
        dr, dc = move_dir
        nr, nc = player.row + dr, player.col + dc

        if nr < 0 or nr >= MAP_H or nc < 0 or nc >= MAP_W:
            continue
        if grid[nr][nc] == '#':
            continue

        # Attack enemy?
        hit = None
        for e in enemies:
            if e.alive and e.row == nr and e.col == nc:
                hit = e
                break

        if hit:
            dmg = max(1, player.attack - random.randint(0, 1))
            hit.hp -= dmg
            gs.score += dmg
            gs.messages.append(f'You hit {hit.name} for {dmg}! ({hit.hp}/{hit.max_hp} HP)')
            gs.particles.append(Particle(hit.row, hit.col, '✦', C_BLOOD, 0.4))
            if hit.hp <= 0:
                hit.alive = False
                bonus = hit.max_hp * 2
                gs.score += bonus
                gs.messages.append(f'{hit.name} is slain! +{bonus} pts')
                gs.particles.append(Particle(hit.row, hit.col, '†', C_BLOOD, 0.6))
        else:
            # Move player
            player.row, player.col = nr, nc

            # Pick up items
            for it in items:
                if not it.collected and it.row == player.row and it.col == player.col:
                    it.collected = True
                    if it.kind == 'potion':
                        heal = it.value
                        player.hp = min(player.max_hp, player.hp + heal)
                        gs.messages.append(f'Drank a potion! Healed {heal} HP.')
                    elif it.kind == 'gold':
                        gs.gold += it.value
                        gs.score += it.value
                        gs.messages.append(f'Picked up {it.value} gold!')
                    elif it.kind == 'sword':
                        player.attack += it.value
                        atk_bonus     += it.value
                        gs.messages.append(f'Found a sword! ATK +{it.value}')
                    elif it.kind == 'shield':
                        def_bonus += it.value
                        gs.messages.append(f'Found a shield! DEF +{it.value}')

            # Stairs?
            if (player.row, player.col) == stair_pos:
                gs.score += gs.level * 100
                gs.messages.append(f'Descended to level {gs.level+1}!')
                gs.level += 1
                return ('next', atk_bonus, def_bonus)

def main(stdscr):
    curses.curs_set(0)
    init_colors()
    stdscr.keypad(True)

    while True:
        if not splash_screen(stdscr):
            return

        gs = GameState()
        atk_bonus = 0
        def_bonus = 0
        outcome = None

        while True:
            result = run_level(stdscr, gs, atk_bonus, def_bonus)
            tag = result[0]
            if tag == 'next':
                _, atk_bonus, def_bonus = result
                if gs.level > 5:   # beat the game after level 5
                    outcome = 'won'
                    break
            elif tag == 'dead':
                outcome = 'dead'
                break
            elif tag == 'quit':
                outcome = 'quit'
                break

        if outcome == 'quit':
            return

        again = game_over_screen(stdscr, gs, won=(outcome == 'won'))
        if not again:
            return


if __name__ == '__main__':
    curses.wrapper(main)

import curses
import random
import time

from .constants import MAP_H, MAP_W, DIRECTIONS, C_WALL, C_FLOOR, C_PLAYER, C_ENEMY, C_ITEM, C_STAIRS, C_UI, C_BLOOD, C_GOLD, C_DARK
from .entities import GameState, Particle
from .mapgen import generate_dungeon, place_entities
from .fov import compute_fov
from .ai import move_enemies
from .render import render, splash_screen, game_over_screen


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

        # Enemies move on a timer for real-time feel
        now = time.time()
        if now - last_enemy_move > 0.35:
            move_enemies(enemies, player, grid, visible, gs)
            last_enemy_move = now
            if player.hp <= 0:
                player.alive = False

        if not player.alive:
            return ('dead',)

        try:
            key = stdscr.getkey()
        except curses.error:
            time.sleep(0.03)
            continue

        if key in ('q', 'Q'):
            return ('quit',)

        move_dir = DIRECTIONS.get(key)
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
                if gs.level > 5:
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

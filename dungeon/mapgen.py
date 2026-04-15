import random
from typing import List, Tuple

from .constants import MAP_H, MAP_W, C_PLAYER, C_ENEMY, C_BLOOD, C_ITEM, C_GOLD
from .entities import Entity, Item, GameState


def generate_dungeon(level: int):
    """BSP-ish room-and-corridor dungeon."""
    grid = [['#'] * MAP_W for _ in range(MAP_H)]
    rooms: List[Tuple[int, int, int, int]] = []   # (r, c, h, w)

    attempts = 40 + level * 5
    for _ in range(attempts):
        rh = random.randint(4, 9)
        rw = random.randint(6, 14)
        r  = random.randint(1, MAP_H - rh - 1)
        c  = random.randint(1, MAP_W - rw - 1)
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
        attack=3 + level, color=C_PLAYER,
    )

    # Stairs in last room
    lr, lc, lh, lw = rooms[-1]
    stair_pos = (lr + lh//2, lc + lw//2)
    grid[stair_pos[0]][stair_pos[1]] = '>'

    # Enemies
    enemy_types = [
        ('r', 'Rat',    4+level,    4+level,    1+level//2, C_ENEMY),
        ('g', 'Goblin', 6+level*2,  6+level*2,  2+level,    C_ENEMY),
        ('o', 'Orc',   10+level*3, 10+level*3,  3+level,    C_BLOOD),
        ('D', 'Dragon',20+level*5, 20+level*5,  5+level*2,  C_BLOOD),
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
        ('potion', '!', C_ITEM, 8),
        ('gold',   '$', C_GOLD, random.randint(5, 20)),
        ('sword',  '/', C_ITEM, 2),
        ('shield', ']', C_ITEM, 1),
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

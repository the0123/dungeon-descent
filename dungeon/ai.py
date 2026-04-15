import random

from .constants import C_BLOOD
from .entities import Particle, GameState


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
                dr, dc = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                nr, nc = e.row+dr, e.col+dc
                if grid[nr][nc] != '#' and (nr, nc) not in occupied:
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
            steps = [(dr, 0) if dr != 0 else None, (0, dc) if dc != 0 else None]
            random.shuffle(steps)
            for step in steps:
                if step is None:
                    continue
                sr, sc = step
                nr, nc = e.row+sr, e.col+sc
                if grid[nr][nc] != '#' and (nr, nc) not in occupied:
                    occupied.discard((e.row, e.col))
                    e.row, e.col = nr, nc
                    occupied.add((e.row, e.col))
                    break

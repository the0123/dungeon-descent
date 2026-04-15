from .constants import MAP_H, MAP_W


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

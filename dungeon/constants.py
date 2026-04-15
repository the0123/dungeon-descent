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

# ── Map dimensions ────────────────────────────────────────────────────────────
MAP_H = 22
MAP_W = 60

# ── Input mapping ─────────────────────────────────────────────────────────────
DIRECTIONS = {
    'w': (-1, 0), 's': (1, 0), 'a': (0, -1), 'd': (0, 1),
    'KEY_UP': (-1, 0), 'KEY_DOWN': (1, 0),
    'KEY_LEFT': (0, -1), 'KEY_RIGHT': (0, 1),
}

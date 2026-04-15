#!/usr/bin/env python3
"""
DUNGEON DESCENT - A Roguelike Console Game
Controls: WASD or Arrow Keys to move, Q to quit, R to restart
"""

import curses
from dungeon import main

if __name__ == '__main__':
    curses.wrapper(main)

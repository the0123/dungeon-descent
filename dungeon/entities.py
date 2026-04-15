import time
from dataclasses import dataclass, field
from typing import List


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

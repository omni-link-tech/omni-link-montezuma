"""Local Montezuma AI engine — BFS pathfinding and enemy avoidance.

This module is the ``make_move`` tool: given the current game state it
runs BFS pathfinding to find the shortest safe path to the current
objective (key or door) while avoiding enemies, and returns the optimal
action (UP, DOWN, LEFT, RIGHT, or STOP).

Ported from the advanced TypeScript agent with the same distance-based
enemy avoidance heuristic that handles all 10 levels.
"""

from __future__ import annotations

from collections import deque
from typing import Any

# Game constants (must match montezuma.py).
TILE_SIZE = 32
COLS = 640 // TILE_SIZE   # 20
ROWS = 720 // TILE_SIZE   # 22 (integer part)
WALL = 1

# Directions: (dx, dy, action_name)
DIRECTIONS = [
    (0, -1, "UP"),
    (0, 1, "DOWN"),
    (-1, 0, "LEFT"),
    (1, 0, "RIGHT"),
]


# ── BFS Pathfinding ─────────────────────────────────────────────────

def _bfs(
    maze: list[list[int]],
    cols: int,
    rows: int,
    enemies: list[dict[str, int]],
    player_x: int,
    player_y: int,
    start: tuple[int, int],
    target: tuple[int, int],
    enemy_radius: int = 3,
) -> list[str] | None:
    """BFS from *start* to *target*, avoiding walls and enemy zones.

    Enemy avoidance uses the same heuristic as the advanced TypeScript
    agent: exact enemy tiles are always blocked; adjacent tiles are only
    blocked if the enemy is within *enemy_radius* Manhattan-distance
    steps of the player.

    Returns a list of actions (e.g. ["RIGHT", "DOWN", ...]) or None if
    no path exists.
    """
    queue: deque[tuple[int, int, list[str]]] = deque()
    queue.append((start[0], start[1], []))
    visited: set[tuple[int, int]] = {start}

    def is_obstacle(x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= cols or y >= rows:
            return True
        if maze[y][x] == WALL:
            return True
        for e in enemies:
            ex, ey = e["x"], e["y"]
            if ex == x and ey == y:
                return True  # exact collision always blocked
            dist_from_player = abs(ex - player_x) + abs(ey - player_y)
            dist_to_point = abs(ex - x) + abs(ey - y)
            if dist_from_player <= enemy_radius and dist_to_point <= 1:
                return True
        return False

    while queue:
        cx, cy, path = queue.popleft()
        if (cx, cy) == target:
            return path

        for dx, dy, action in DIRECTIONS:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in visited and not is_obstacle(nx, ny):
                visited.add((nx, ny))
                queue.append((nx, ny, path + [action]))

    return None


def _bfs_fallback(
    maze: list[list[int]],
    cols: int,
    rows: int,
    enemies: list[dict[str, int]],
    start: tuple[int, int],
    target: tuple[int, int],
) -> list[str] | None:
    """Fallback BFS that ignores enemy adjacency — only avoids exact
    enemy tiles.  Used when the primary BFS finds no path due to dense
    enemy coverage.
    """
    queue: deque[tuple[int, int, list[str]]] = deque()
    queue.append((start[0], start[1], []))
    visited: set[tuple[int, int]] = {start}

    enemy_tiles = {(e["x"], e["y"]) for e in enemies}

    def is_obstacle(x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= cols or y >= rows:
            return True
        if maze[y][x] == WALL:
            return True
        if (x, y) in enemy_tiles:
            return True
        return False

    while queue:
        cx, cy, path = queue.popleft()
        if (cx, cy) == target:
            return path

        for dx, dy, action in DIRECTIONS:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in visited and not is_obstacle(nx, ny):
                visited.add((nx, ny))
                queue.append((nx, ny, path + [action]))

    return None


# ── Action decision ──────────────────────────────────────────────────

def decide_action(state: dict[str, Any]) -> str:
    """Decide the next movement action based on the current game state.

    Returns ``'UP'``, ``'DOWN'``, ``'LEFT'``, ``'RIGHT'``, or ``'STOP'``.
    """
    maze = state.get("maze", [])
    cols = state.get("cols", COLS)
    rows = state.get("rows", ROWS)
    enemies = state.get("enemies", [])
    player_x = state.get("player_x", 0)
    player_y = state.get("player_y", 0)
    has_key = state.get("has_key", False)

    start = (player_x, player_y)

    if has_key:
        target = (state.get("door_x", 0), state.get("door_y", 0))
    else:
        target = (state.get("key_x", 0), state.get("key_y", 0))

    # Primary BFS with enemy avoidance radius.
    path = _bfs(maze, cols, rows, enemies, player_x, player_y, start, target)

    # Fallback: if no safe path, try ignoring enemy adjacency zones.
    if path is None:
        path = _bfs_fallback(maze, cols, rows, enemies, start, target)

    if path and len(path) > 0:
        return path[0]

    return "STOP"


# ── State summary (for OmniLink memory) ─────────────────────────────

def state_summary(state: dict[str, Any]) -> str:
    """Build a concise text summary of the current game state."""
    lives = state.get("lives", 0)
    score = state.get("score", 0)
    level = state.get("level", 1)
    play_time = state.get("play_time", 0)
    game_state = state.get("game_state", "UNKNOWN")
    has_key = state.get("has_key", False)
    player_x = state.get("player_x", 0)
    player_y = state.get("player_y", 0)
    enemies = state.get("enemies", [])

    minutes = int(play_time) // 60
    seconds = int(play_time) % 60

    objective = "reach DOOR" if has_key else "find KEY"

    return (
        f"Game state: {game_state}\n"
        f"Score: {score} | Level: {level} | Lives: {lives}\n"
        f"Play time: {minutes}m {seconds}s\n"
        f"Objective: {objective}\n"
        f"Player position: ({player_x}, {player_y})\n"
        f"Enemies: {len(enemies)}\n"
        f"Has key: {has_key}"
    )

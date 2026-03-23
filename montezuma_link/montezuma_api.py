"""HTTP client for the Montezuma game server."""

from __future__ import annotations

import json
from typing import Any

import requests

SERVER_URL = "http://127.0.0.1:5003"

# Reuse a persistent session for connection pooling.
_session = requests.Session()


def get_state() -> dict[str, Any]:
    """Fetch the current game state from the server.

    Returns the parsed game state dict with keys: maze, player_x, player_y,
    has_key, key_x, key_y, door_x, door_y, enemies, score, level, lives,
    play_time, game_state, cols, rows.
    """
    r = _session.get(f"{SERVER_URL}/data", timeout=2)
    data = r.json()
    payload = data.get("payload", "{}")
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def send_action(action: str) -> None:
    """Send a single action (UP, DOWN, LEFT, RIGHT, STOP, START, RESUME, PAUSE) to the game."""
    _session.post(
        f"{SERVER_URL}/callback",
        json={"action": action},
        timeout=2,
    )


def send_actions(actions: list[str]) -> None:
    """Send a batch of actions to the game."""
    _session.post(
        f"{SERVER_URL}/callback",
        json={"actions": actions},
        timeout=2,
    )

"""Play Montezuma using OmniLink tool calling.

The AI agent calls the ``make_move`` tool, which acts as a local
Montezuma AI controller.  The model never sees the game — it simply
triggers the tool.  The tool reads the game state, runs BFS pathfinding,
and moves the player accordingly.

This keeps API credit usage to a minimum (one call to kick off).

Usage
-----
    python -u play_montezuma.py
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

# ── Path setup ─────────────────────────────────────────────────────────
_HERE = str(pathlib.Path(__file__).resolve().parent)
LIB_PATH = str(pathlib.Path(__file__).resolve().parents[3] / "omnilink-lib" / "src")
if _HERE in sys.path:
    sys.path.remove(_HERE)
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

from omnilink.tool_runner import ToolRunner

if _HERE not in sys.path:
    sys.path.append(_HERE)

from montezuma_api import get_state, send_action
from montezuma_engine import decide_action, state_summary


class MontezumaRunner(ToolRunner):
    agent_name = "montezuma-agent"
    display_name = "Montezuma"
    tool_description = "Run Montezuma AI."
    poll_interval = 0.06

    def __init__(self) -> None:
        self._last_score = 0
        self._last_lives = -1
        self._last_level = -1

    def get_state(self) -> dict[str, Any]:
        return get_state()

    def execute_action(self, state: dict[str, Any]) -> None:
        if state.get("game_state") == "PLAY":
            send_action(decide_action(state))

    def state_summary(self, state: dict[str, Any]) -> str:
        return state_summary(state)

    def is_game_over(self, state: dict[str, Any]) -> bool:
        return state.get("game_state") in ("GAMEOVER", "WIN")

    def game_over_message(self, state: dict[str, Any]) -> str:
        gs = state.get("game_state")
        score = state.get("score", 0)
        level = state.get("level", 1)
        if gs == "WIN":
            return f"YOU WIN! — Final score: {score}, All 10 levels complete!"
        return f"GAME OVER — Final score: {score}, Level: {level}"

    def on_start(self) -> None:
        try:
            send_action("START")
            print("  Game started.")
        except Exception:
            pass

    def log_events(self, state: dict[str, Any]) -> None:
        score = state.get("score", 0)
        lives = state.get("lives", 0)
        level = state.get("level", 1)

        if score != self._last_score:
            has_key = state.get("has_key", False)
            label = "Key" if has_key and score - self._last_score == 50 else "Door"
            print(f"  Score: {score}  (+{score - self._last_score}) [{label}]")
            self._last_score = score
        if lives != self._last_lives:
            if self._last_lives > 0 and lives < self._last_lives:
                print(f"  ** Life lost! Lives: {lives}")
            self._last_lives = lives
        if level != self._last_level:
            print(f"  Level: {level}")
            self._last_level = level


if __name__ == "__main__":
    MontezumaRunner().run()

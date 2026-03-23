# OmniLink Montezuma Benchmark

A Pygame maze exploration game inspired by Montezuma's Revenge, controlled by a
local AI engine through the OmniLink platform via **tool calling**.  The AI agent
uses BFS pathfinding to navigate mazes, avoid enemies, collect keys, and unlock
doors across 10 increasingly difficult levels.

This demo showcases four core OmniLink features:

| Feature | How it is used |
|---|---|
| **Tool Calling** | Agent calls `make_move` — the platform forwards execution to the local AI controller |
| **Commands** | Agent outputs `Command: stop_game` to end the game early |
| **Short-Term Memory** | Game state (score, lives, level, objective) is saved periodically |
| **Chat API** | The agent can be asked about the game state at any time from the OmniLink UI |

---

## Benchmark Results

| Metric | Value |
|---|---|
| **Final Score** | 2,550 |
| **Levels Cleared** | 10/10 (GAME WON) |
| **Lives Used** | 3/5 (2 remaining) |
| **Play Time** | 50 seconds |
| **API Calls** | 1 kick-off + ~1 review |
| **AI Strategy** | BFS pathfinding with enemy avoidance radius |

This is the only benchmark where the agent **completes the entire game**.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.9 or later |
| OmniKey | Sign up at https://www.omnilink-agents.com |

Python packages:

```
pip install pygame requests
```

---

## Quick Start

You need **two terminals**.

### Step 1 — Start the game server (Terminal 1)

```bash
cd omnilink-montezuma
python server_wrapper.py
```

This launches:
- The **Pygame window** — the Montezuma maze game
- An **HTTP API** on **http://localhost:5003** for state polling and action sending

### Step 2 — Run the AI agent (Terminal 2)

```bash
cd montezuma_link
python -u play_montezuma.py
```

---

## Architecture & Components

The core architecture matches the OmniLink suite (Tetris, Breakout, etc.):

- **`montezuma.py` (The Game Engine)**: A 2D Pygame tile-based maze environment.
- **`server_wrapper.py` (Backend REST API Bridge)**: HTTP + MQTT bridge.
  - **`GET /data` (Port 5003)**: Full JSON state — maze grid, player, key, door, enemies.
  - **`POST /callback` (Port 5003)**: Accepts movement actions (UP, DOWN, LEFT, RIGHT, START).
  - **MQTT (`olink/commands`)**: Pause/resume control.
  - **MQTT (`olink/context`)**: Event-driven telemetry (life lost, level change, state change).
- **`montezuma_link/montezuma_engine.py`**: BFS pathfinding with enemy avoidance.
- **`montezuma_link/play_montezuma.py`**: OmniLink integration and control loop.

### AI Strategy (BFS + Enemy Avoidance)

1. **Objective**: Find KEY first, then navigate to DOOR.
2. **Primary BFS**: Paths around walls and enemy zones (radius-based avoidance).
3. **Fallback BFS**: If no safe path exists, ignores adjacency zones and only avoids exact enemy tiles.
4. **Enemy Avoidance**: Exact enemy tiles always blocked. Adjacent tiles blocked when enemy is within Manhattan distance 3 of the player.

### Game Mechanics

| Parameter | Value |
|---|---|
| Grid size | 20 x 22 tiles (32px each) |
| Lives | 5 |
| Levels | 10 |
| Enemies | Red skulls, increasing per level |
| Scoring | +50 per key, +200 per door |
| Win condition | Clear all 10 levels |

---

## Key Files

| File | Description |
|---|---|
| `montezuma_link/play_montezuma.py` | Main script — OmniLink integration, control loop |
| `montezuma_link/montezuma_engine.py` | AI controller — BFS pathfinding, enemy avoidance |
| `montezuma_link/montezuma_api.py` | HTTP client for polling state and sending actions |
| `montezuma.py` | Pygame game engine — maze, enemies, rendering |
| `server_wrapper.py` | HTTP + MQTT bridge wrapping the Pygame game ||

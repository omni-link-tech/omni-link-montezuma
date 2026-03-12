# OmniLink Montezuma's Return Project

This directory contains a Pygame implementation of a tile-based maze exploration game directly inspired by Montezuma's Revenge, augmented with the OmniLink REST/MQTT interaction architecture.

## Features Added & Game Mechanics
- **Core Rules**: Traverse the maze to retrieve the Key (Yellow) to unlock the Door (Green) and advance levels.
- **Enemies**: Red skulls patrol the maze randomly. Contact results in death (5 lives).
- **Macro-Action API**: Capable of accepting step translation directives (`UP`, `DOWN`, `LEFT`, `RIGHT`, `STOP`) from AI tools.
- **Grid Environment**: Perfect for matrix-based pathfinding algorithms.

## Architecture & Components

The core architecture strictly matches the OmniLink suite (Tetris, Breakout, etc.):

- **`montezuma.py` (The Game Engine)**: A 2D Pygame environment.
- **`server_wrapper.py` (Backend REST API Bridge)**: The server connecting the game to the AI endpoints.
  - **`GET /data` (Port 5003)**: Emits current JSON state of the 2D maze array, player, key, door, and enemies.
  - **`POST /callback` (Port 5003)**: Returns an array of game actions.
  - **MQTT (`olink/commands`)**: Enables toggling pause states in real-time.
  - **MQTT (`olink/context`)**: Publishes summary telemetry data of the active game (score, lives, level tracking).
- **`agent.ts`**: The intelligent omniscient agent. It polls `/data` and executes Breadth-First Search (BFS) mathematically to map the shortest path to objectives while dynamically interpreting enemy coordinates as impassable walls to avoid death.

## How to Run

1. **Launch the Server & Game Environment**:
   Starting the HTTP Server and Pygame Client together:
   ```bash
   python server_wrapper.py
   ```
   At this point, the game screen will appear in an idle/waiting state.

2. **Launch the Agent**:
   Transpile and fire up the Node isolated agent.
   ```bash
   npx ts-node agent.ts
   ```
   The agent will immediately link up and start pathfinding toward the key and subsequent door to conquer the levels autonomously.

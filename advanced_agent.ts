/**
 * OmniLink Montezuma Advanced Agent  (Levels 1–10)
 * ─────────────────────────────────────────────────────────────
 * Target : Browser / OmniLink Tool environment (classic Worker)
 *
 * Architecture:
 *   GET  http://localhost:5003/data      ← maze, player, key, door, enemies
 *   POST http://localhost:5003/callback  → action: UP|DOWN|LEFT|RIGHT|STOP
 *   MQTT ws://localhost:9001  olink/commands  ← pause/resume
 *
 * Improvements over basic agent:
 *   - Only avoids enemy tiles that are within 3 steps of the player,
 *     allowing aggressive pathfinding through high-density levels.
 *   - Handles all 10 levels through to the WIN state.
 */

(async () => {

    // ── Logging flags ─────────────────────────────────────────────────────────────
    const LOG_DECISION = true;
    const LOG_EVENTS = true;
    const LOG_ERRORS = true;
    const LOG_MQTT = true;

    // ── Config ────────────────────────────────────────────────────────────────────
    const API_URL = "http://localhost:5003";
    const POLL_DELAY_MS = 60;
    const MQTT_WS_URL = "ws://localhost:9001";
    const CMD_TOPIC = "olink/commands";

    // ── Interfaces ────────────────────────────────────────────────────────────────
    interface Point { x: number; y: number; }

    interface GameState {
        type: "state";
        maze: number[][];
        player_x: number;
        player_y: number;
        has_key: boolean;
        key_x: number;
        key_y: number;
        door_x: number;
        door_y: number;
        enemies: Point[];
        score: number;
        level: number;
        lives: number;
        play_time: number;
        game_state: string;
        cols: number;
        rows: number;
    }

    interface PyState {
        command: "IDLE" | "ACTIVATE";
        payload: string;
        version: number;
    }

    // ── State variables ───────────────────────────────────────────────────────────
    let lastVersion = -1;
    let lastScore = -1;
    let lastLevel = -1;
    let lastLives = -1;
    let lastState = "";

    // ── Advanced BFS Pathfinding ──────────────────────────────────────────────────
    function getShortestPath(
        state: GameState,
        start: Point,
        target: Point
    ): ("UP" | "DOWN" | "LEFT" | "RIGHT")[] | null {
        const queue: { p: Point; path: ("UP" | "DOWN" | "LEFT" | "RIGHT")[] }[] = [
            { p: start, path: [] },
        ];
        const visited = new Set<string>();
        visited.add(`${start.x},${start.y}`);

        // More lenient obstacle check: only care about enemies very close to player
        const isObstacle = (x: number, y: number): boolean => {
            if (x < 0 || y < 0 || x >= state.cols || y >= state.rows) return true;
            if (state.maze[y][x] === 1) return true;
            for (const e of state.enemies) {
                if (e.x === x && e.y === y) return true; // exact collision always blocked
                // Only avoid adjacent tiles if the enemy is within 3 steps of the player
                const distFromPlayer = Math.abs(e.x - state.player_x) + Math.abs(e.y - state.player_y);
                const distToPoint = Math.abs(e.x - x) + Math.abs(e.y - y);
                if (distFromPlayer <= 3 && distToPoint <= 1) return true;
            }
            return false;
        };

        while (queue.length > 0) {
            const { p, path } = queue.shift()!;
            if (p.x === target.x && p.y === target.y) return path;

            const moves = [
                { dir: "UP" as const, dx: 0, dy: -1 },
                { dir: "DOWN" as const, dx: 0, dy: 1 },
                { dir: "LEFT" as const, dx: -1, dy: 0 },
                { dir: "RIGHT" as const, dx: 1, dy: 0 },
            ];
            moves.sort(() => Math.random() - 0.5);

            for (const m of moves) {
                const nx = p.x + m.dx;
                const ny = p.y + m.dy;
                const key = `${nx},${ny}`;
                if (!visited.has(key) && !isObstacle(nx, ny)) {
                    visited.add(key);
                    queue.push({ p: { x: nx, y: ny }, path: [...path, m.dir] });
                }
            }
        }
        return null;
    }

    function decideAction(state: GameState): "UP" | "DOWN" | "LEFT" | "RIGHT" | "STOP" {
        const start = { x: state.player_x, y: state.player_y };
        const target = state.has_key
            ? { x: state.door_x, y: state.door_y }
            : { x: state.key_x, y: state.key_y };

        const path = getShortestPath(state, start, target);
        if (path && path.length > 0) {
            if (LOG_DECISION && Math.random() < 0.05)
                console.log(`[AI] Path to ${state.has_key ? "door" : "key"}: ${path.length} steps`);
            return path[0];
        }
        return "STOP";
    }

    // ── Main Poll Loop ────────────────────────────────────────────────────────────
    async function agentLoop(): Promise<void> {
        try {
            const res = await fetch(`${API_URL}/data`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const wrapper: PyState = await res.json();

            if (wrapper.command === "ACTIVATE" && wrapper.version > lastVersion) {
                lastVersion = wrapper.version;
                const state: GameState = JSON.parse(wrapper.payload);

                if (state.score !== lastScore && lastScore !== -1)
                    if (LOG_EVENTS) console.log(`[GAME] Score: ${state.score} (+${state.score - lastScore})`);
                lastScore = state.score;

                if (state.level !== lastLevel && lastLevel !== -1)
                    if (LOG_EVENTS) console.log(`[GAME] 🎉 Level Up → ${state.level}`);
                lastLevel = state.level;

                if (state.lives !== lastLives && lastLives !== -1)
                    if (LOG_EVENTS) console.log(`[GAME] Lives left: ${state.lives}`);
                lastLives = state.lives;

                if (state.game_state !== lastState) {
                    if (LOG_EVENTS) console.log(`[GAME] State: ${state.game_state}`);
                    lastState = state.game_state;
                }

                if (state.game_state === "WIN") {
                    console.log("╔══════════════════════════════════════════════╗");
                    console.log("║  🏆  ALL 10 LEVELS COMPLETE — YOU WIN!       ║");
                    console.log("╚══════════════════════════════════════════════╝");
                    return;
                }

                if (state.game_state === "PLAY") {
                    const action = decideAction(state);
                    await fetch(`${API_URL}/callback`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ action, version: wrapper.version }),
                    });
                }
            }
        } catch (err: unknown) {
            if (LOG_ERRORS) {
                const msg = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
                console.error(`[AGENT] Error: ${msg}`);
            }
        }
    }

    // ── MQTT pause/resume ─────────────────────────────────────────────────────────
    const _g = globalThis as Record<string, unknown>;

    function sendMqttCmd(cmd: "pause" | "resume"): void {
        const client = _g["mqttClient"] as any;
        if (!client) { console.warn("[MQTT] Not connected."); return; }
        client.publish(CMD_TOPIC, JSON.stringify({ command: cmd }));
        if (LOG_MQTT) console.log(`[MQTT] → '${CMD_TOPIC}': ${cmd}`);
    }

    _g["pauseGame"] = () => sendMqttCmd("pause");
    _g["resumeGame"] = () => sendMqttCmd("resume");

    async function initMqtt(): Promise<void> {
        try {
            const lib = _g["mqtt"] as any;
            if (!lib) { console.warn("[MQTT] No global mqtt lib."); return; }
            const client = lib.connect(MQTT_WS_URL, { clientId: `montezuma-advanced-${Date.now()}` });
            client.on("connect", () => {
                if (LOG_MQTT) console.log(`[MQTT] ✅ Connected`);
                _g["mqttClient"] = client;
                client.subscribe(CMD_TOPIC, (err: Error | null) => {
                    if (err) {
                        if (LOG_ERRORS) console.error(`[MQTT] Subscribe error: ${err.message}`);
                    } else {
                        if (LOG_MQTT) console.log(`[MQTT] 📥 Subscribed to '${CMD_TOPIC}'`);
                    }
                });
            });
            client.on("message", (topic: string, payload: any) => {
                if (LOG_MQTT) console.log(`[MQTT] ← '${topic}': ${String(payload)}`);
            });
            client.on("error", (e: Error) => { if (LOG_ERRORS) console.error("[MQTT]", e.message); });
            client.on("close", () => { if (LOG_MQTT) console.log("[MQTT] Disconnected."); });
        } catch (err) {
            if (LOG_ERRORS) console.error("[MQTT] Init failed:", err);
        }
    }

    // ── Bootstrap ─────────────────────────────────────────────────────────────────
    console.log("╔══════════════════════════════════════════════╗");
    console.log("║  💀  OmniLink Montezuma ADVANCED Agent       ║");
    console.log("║      (Levels 1–10, aggressive pathfinding)   ║");
    console.log("╚══════════════════════════════════════════════╝");
    console.log(`[CONFIG] API: ${API_URL}  MQTT: ${MQTT_WS_URL}`);

    initMqtt();

    async function runLoop(): Promise<void> {
        await agentLoop();
        setTimeout(runLoop, POLL_DELAY_MS);
    }

    runLoop();

})();

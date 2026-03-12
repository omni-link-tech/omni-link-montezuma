import sys, re, threading, time, json
import pygame
from http.server import HTTPServer, BaseHTTPRequestHandler
import paho.mqtt.client as mqtt

from montezuma import Montezuma

# ── Configuration ──────────────────────────────────────────────────────────────
HTTP_PORT     = 5003
MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
CMD_TOPIC     = "olink/commands"
CTX_TOPIC     = "olink/context"
PUBLISH_EVERY = 20

# ── Shared state ───────────────────────────────────────────────────────────────
_GAME: Montezuma = None
_VERSION      = 0

# ──────────────────────────────────────────────────────────────────────────────
# State builder
# ──────────────────────────────────────────────────────────────────────────────
def _build_state(game: Montezuma) -> dict:
    return {
        "type":         "state",
        "maze":         [row[:] for row in game.maze],
        "player_x":     game.player_x,
        "player_y":     game.player_y,
        "has_key":      game.has_key,
        "key_x":        game.key_x,
        "key_y":        game.key_y,
        "door_x":       game.door_x,
        "door_y":       game.door_y,
        "enemies":      [{"x": e["x"], "y": e["y"]} for e in game.enemies],
        "score":        game.score,
        "level":        game.level,
        "lives":        game.lives,
        "play_time":    game.play_time,
        "game_state":   game.state,   # TITLE | PLAY | PAUSE | GAMEOVER
        "cols":         len(game.maze[0]),
        "rows":         len(game.maze),
    }

# ──────────────────────────────────────────────────────────────────────────────
# Pause / resume parser
# ──────────────────────────────────────────────────────────────────────────────
def _parse_cmd(raw: str):
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("command", "action", "cmd"):
                if key in data:
                    return str(data[key])
        if isinstance(data, str):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r'["\']?(?:command|action|cmd)["\']?\s*:\s*["\']?(\w+)["\']?', raw, re.I)
    if m:
        return m.group(1)
    if raw.lower() in ("pause", "resume", "pause_game", "resume_game"):
        return raw
    return None

def _apply_cmd(cmd: str):
    game = _GAME
    if game is None:
        return
    cmd_l = cmd.strip().lower().strip("\"'")
    if cmd_l in ("pause", "pause_game"):
        if game.state == "PLAY":
            game.toggle_pause()
            print(f"[MQTT] ⏸  PAUSED  (cmd='{cmd}')")
    elif cmd_l in ("resume", "resume_game"):
        if game.state == "PAUSE":
            game.toggle_pause()
            print(f"[MQTT] ▶  RESUMED  (cmd='{cmd}')")
    else:
        print(f"[MQTT] Unknown command: '{cmd}'")

# ──────────────────────────────────────────────────────────────────────────────
# MQTT
# ──────────────────────────────────────────────────────────────────────────────
def _on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        print(f"[MQTT] ✅ Connected to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(CMD_TOPIC)
        print(f"[MQTT] Subscribed to '{CMD_TOPIC}' (commands)")
        client.subscribe(CTX_TOPIC)
        print(f"[MQTT] Subscribed to '{CTX_TOPIC}' (loopback verify)")
    else:
        print(f"[MQTT] ❌ Connection failed rc={rc}")

def _on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    if msg.topic == CTX_TOPIC:
        # Loopback: we published this ourselves — just confirm receipt
        print(f"[MQTT] ✓ loopback on '{msg.topic}'")
        return
    print(f"[MQTT] ← '{msg.topic}': {raw}")
    cmd = _parse_cmd(raw)
    if cmd:
        _apply_cmd(cmd)
    else:
        print(f"[MQTT] ⚠ Unrecognised payload on '{msg.topic}': {raw[:120]}")

def _publish_state(client, reason: str = "heartbeat"):
    """Publish a montezuma_summary to olink/context."""
    if _GAME is None:
        return
    g = _GAME
    payload = {
        "topic":     "montezuma_summary",
        "reason":    reason,
        "score":     g.score,
        "level":     g.level,
        "lives":     g.lives,
        "state":     g.state,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    client.publish(CTX_TOPIC, json.dumps(payload))
    print(f"[MQTT] → '{CTX_TOPIC}' [{reason}]: score={g.score} level={g.level} lives={g.lives} state={g.state}")

def _publisher_loop(client):
    """Event-driven publisher: fires immediately on key events, otherwise every PUBLISH_EVERY seconds."""
    last_heartbeat = time.time()
    last_lives  = None
    last_level  = None
    last_state  = None

    while True:
        time.sleep(0.25)  # check 4× per second for responsiveness
        if _GAME is None:
            continue

        g = _GAME
        now = time.time()

        # Detect life loss
        if last_lives is not None and g.lives < last_lives:
            print(f"[EVENT] 💔 Life lost! {last_lives} → {g.lives}")
            _publish_state(client, reason="life_lost")
            last_heartbeat = now  # reset heartbeat timer
        last_lives = g.lives

        # Detect level change
        if last_level is not None and g.level != last_level:
            print(f"[EVENT] 🎉 Level change: {last_level} → {g.level}")
            _publish_state(client, reason="level_change")
            last_heartbeat = now
        last_level = g.level

        # Detect game state change (PLAY / PAUSE / GAMEOVER / WIN / TITLE)
        if last_state is not None and g.state != last_state:
            print(f"[EVENT] 🔄 State change: {last_state} → {g.state}")
            _publish_state(client, reason=f"state_{g.state.lower()}")
            last_heartbeat = now
        last_state = g.state

        # Heartbeat fallback
        if now - last_heartbeat >= PUBLISH_EVERY:
            _publish_state(client, reason="heartbeat")
            last_heartbeat = now

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = _on_connect
    client.on_message = _on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT] WARNING: Cannot connect – {e}")
        return
    threading.Thread(target=_publisher_loop, args=(client,), daemon=True, name="mqtt-pub").start()

# ──────────────────────────────────────────────────────────────────────────────
# HTTP API
# ──────────────────────────────────────────────────────────────────────────────
class MontezumaAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        global _VERSION
        if self.path != "/data":
            self.send_error(404); return
        if _GAME is None:
            self.send_error(503, "Game not ready"); return

        _VERSION += 1
        game = _GAME
        payload = {
            "command": "ACTIVATE" if game.state == "PLAY" else "IDLE",
            "payload": json.dumps(_build_state(game)),
            "version": _VERSION,
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/callback":
            self.send_error(404); return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            data   = json.loads(body)
            action = data.get("action")
            actions = data.get("actions")
            
            allowed = ("UP", "DOWN", "LEFT", "RIGHT", "STOP")
            if isinstance(actions, list) and len(actions) > 0 and _GAME:
                for act in actions:
                    act_str = str(act).upper()
                    if act_str in allowed:
                        _GAME.pending_actions.append(act_str)
            elif action and isinstance(action, str) and _GAME:
                act_str = action.upper()
                if act_str in allowed:
                    _GAME.pending_actions.append(act_str)
        except Exception as e:
            print(f"[HTTP] /callback parse error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

def run_http():
    server = HTTPServer(("", HTTP_PORT), MontezumaAPIHandler)
    print(f"[HTTP] API on port {HTTP_PORT}")
    server.serve_forever()

# ──────────────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=run_http,   daemon=True, name="http").start()
    start_mqtt()

    print("[Game] Initialising Montezuma…")
    game = Montezuma()
    _GAME = game

    print("[Game] Ready – waiting for agent commands on port", HTTP_PORT)
    try:
        game.run()
    except SystemExit:
        pass
    except Exception as exc:
        print(f"[Game] Crash: {exc}")
    finally:
        print("[Game] Exiting.")
        pygame.quit()
        sys.exit(0)

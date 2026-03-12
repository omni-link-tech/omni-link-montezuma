import pygame
import random
import sys

# Config
WIDTH, HEIGHT = 640, 720
FPS = 15 # Lower frame rate for grid movement pacing
TILE_SIZE = 32

COLS = WIDTH // TILE_SIZE
ROWS = HEIGHT // TILE_SIZE

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (50, 50, 200)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
EMPTY_COLOR = (82, 82, 82)
GRID_COLOR = (51, 51, 51)
WALL_COLOR = (27, 27, 27)

# Maze Tiles
EMPTY = 0
WALL = 1

class Montezuma:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.game_surface = pygame.Surface((WIDTH, HEIGHT))
        self.is_fullscreen = False
        self.old_size = (WIDTH, HEIGHT)
        pygame.display.set_caption("OmniLink Montezuma")
        self.clock = pygame.time.Clock()
        try:
            self.font_large = pygame.font.Font(pygame.font.match_font('arial', bold=True), 60)
            self.font_small = pygame.font.Font(pygame.font.match_font('arial', bold=False), 30)
        except:
            self.font_large = pygame.font.SysFont("arial", 60, bold=True)
            self.font_small = pygame.font.SysFont("arial", 30, bold=False)
            
        self.reset_game()
        self.state = "TITLE"  # TITLE, PLAY, PAUSE, GAMEOVER, WIN
        self.pending_actions = []

    def generate_maze(self):
        # Basic BSP or simple generated layout
        self.maze = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        
        # Border walls
        for r in range(ROWS):
            self.maze[r][0] = WALL
            self.maze[r][COLS-1] = WALL
        for c in range(COLS):
            self.maze[0][c] = WALL
            self.maze[ROWS-1][c] = WALL
            
        # Hardcoded random maze obstacles scaling with level.
        # Cap at level 7 difficulty for levels 8-10 so the endgame stays
        # challenging but not brutally hard.
        effective_level = min(self.level, 7)
        obstacle_chance = 0.1 + (effective_level * 0.03)  # max ~31% at level 7
        for r in range(4, ROWS-4, 2):
            for c in range(4, COLS-4):
                if random.random() < obstacle_chance:
                    self.maze[r][c] = WALL
        
        # Safe spawn points
        self.maze[2][2] = EMPTY
        self.maze[ROWS-3][COLS-3] = EMPTY

    def spawn_entities(self):
        self.player_x = 2
        self.player_y = 2
        self.has_key = False
        
        # Spawn Key
        while True:
            r = random.randint(2, ROWS-3)
            c = random.randint(2, COLS-3)
            if self.maze[r][c] == EMPTY and (r, c) != (2, 2):
                self.key_x, self.key_y = c, r
                break
                
        # Spawn Door
        while True:
            r = random.randint(2, ROWS-3)
            c = random.randint(2, COLS-3)
            if self.maze[r][c] == EMPTY and (r, c) != (2, 2) and (r, c) != (self.key_y, self.key_x):
                self.door_x, self.door_y = c, r
                break
                
        # Spawn Enemies scaling with level.
        # Cap enemy count at 13 for levels 8-10 to keep the endgame fair.
        self.enemies = []
        num_enemies = 1 + (min(self.level, 6) * 2)  # max 13 enemies (at level 6+)
        for _ in range(num_enemies):
            while True:
                r = random.randint(4, ROWS-3)
                c = random.randint(4, COLS-3)
                if self.maze[r][c] == EMPTY and abs(r - 2) > 3 and abs(c - 2) > 3:
                     self.enemies.append({"x": c, "y": r, "dx": random.choice([-1, 1, 0]), "dy": random.choice([-1, 1, 0])})
                     break

    def reset_game(self):
        self.score = 0
        self.lives = 5
        self.level = 1
        self.play_time = 0.0
        self._flash_frames = 0   # red-flash countdown on life loss
        self.start_ticks = pygame.time.get_ticks()
        self.reset_level()
        
    def reset_level(self):
        self.generate_maze()
        self.spawn_entities()

    def toggle_fullscreen(self):
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        if self.is_fullscreen:
            self.old_size = self.screen.get_size()
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode(getattr(self, "old_size", (WIDTH, HEIGHT)), pygame.RESIZABLE)
        
    def toggle_pause(self):
        if self.state == "PLAY":
            self.state = "PAUSE"
        elif self.state == "PAUSE":
            self.state = "PLAY"
            self.start_ticks = pygame.time.get_ticks() - int(self.play_time * 1000)

    def step(self):
        if self.state != "PLAY":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.VIDEORESIZE:
                    if not getattr(self, "is_fullscreen", False):
                        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_SPACE:
                        if self.state in ("TITLE", "GAMEOVER", "WIN"):
                            self.reset_game()
                            self.state = "PLAY"
                            self.start_ticks = pygame.time.get_ticks()
                        else:
                            self.toggle_pause()
            return
            
        self.play_time = (pygame.time.get_ticks() - self.start_ticks) / 1000.0

        # Handle events and queue
        action = None
        if self.pending_actions:
            action = self.pending_actions.pop(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.VIDEORESIZE:
                if not getattr(self, "is_fullscreen", False):
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    self.toggle_pause()
                    return
                elif event.key == pygame.K_UP: action = "UP"
                elif event.key == pygame.K_DOWN: action = "DOWN"
                elif event.key == pygame.K_LEFT: action = "LEFT"
                elif event.key == pygame.K_RIGHT: action = "RIGHT"

        nx, ny = self.player_x, self.player_y
        if action == "UP": ny -= 1
        elif action == "DOWN": ny += 1
        elif action == "LEFT": nx -= 1
        elif action == "RIGHT": nx += 1

        if 0 <= nx < COLS and 0 <= ny < ROWS:
            if self.maze[ny][nx] != WALL:
                self.player_x = nx
                self.player_y = ny
                
        # Collect Key
        if self.player_x == self.key_x and self.player_y == self.key_y and not self.has_key:
            self.has_key = True
            self.score += 50
            
        # Enter Door
        if self.player_x == self.door_x and self.player_y == self.door_y and self.has_key:
            self.score += 200
            self.level += 1
            if self.level > 10:
                self.state = "WIN"
            else:
                self.reset_level()
            return

        # Enemy Movement (Move randomly every frame, restricted by walls)
        # Enemies speed up slightly based on play_time by moving more frequently theoretically, 
        # but in grid base we just let them move 1 block per tick.
        for e in self.enemies:
            moves = [(1,0), (-1,0), (0,1), (0,-1)]
            random.shuffle(moves)
            for dx, dy in moves:
                ex, ey = e["x"] + dx, e["y"] + dy
                if 0 <= ex < COLS and 0 <= ey < ROWS and self.maze[ey][ex] != WALL:
                    e["x"], e["y"] = ex, ey
                    break

        # Check death
        for e in self.enemies:
            if e["x"] == self.player_x and e["y"] == self.player_y:
                self.lives -= 1
                self._flash_frames = 8   # trigger red flash
                if self.lives <= 0:
                    self.state = "GAMEOVER"
                else:
                    self.spawn_entities()
                return

    def draw(self):
        self.game_surface.fill(EMPTY_COLOR)
        
        # Maze Walls & Grid
        for r in range(ROWS):
            for c in range(COLS):
                rect = (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if self.maze[r][c] == WALL:
                    pygame.draw.rect(self.game_surface, WALL_COLOR, rect)
                else:
                    pygame.draw.rect(self.game_surface, GRID_COLOR, rect, 1)
                    
        # Door
        pygame.draw.rect(self.game_surface, ORANGE, (self.door_x*TILE_SIZE, self.door_y*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # Key
        if not self.has_key:
            pygame.draw.rect(self.game_surface, YELLOW, (self.key_x*TILE_SIZE, self.key_y*TILE_SIZE, TILE_SIZE, TILE_SIZE))
            
        # Enemies
        for e in self.enemies:
            pygame.draw.rect(self.game_surface, RED, (e["x"]*TILE_SIZE, e["y"]*TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Player
        pygame.draw.rect(self.game_surface, CYAN, (self.player_x*TILE_SIZE, self.player_y*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # UI overlays
        if self.state == "TITLE":
            # Just dim
            s = pygame.Surface((WIDTH,HEIGHT))
            s.set_alpha(128)
            s.fill((0,0,0))
            self.game_surface.blit(s, (0,0))
            t = self.font_small.render("PRESS SPACE TO START", True, WHITE)
            self.game_surface.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
        elif self.state == "GAMEOVER":
            t = self.font_large.render("GAME OVER", True, RED)
            self.game_surface.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 50))
            t2 = self.font_small.render("PRESS SPACE TO RESTART", True, WHITE)
            self.game_surface.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 50))
        elif self.state == "WIN":
            t = self.font_large.render("YOU WIN", True, YELLOW)
            self.game_surface.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 50))
            t2 = self.font_small.render("PRESS SPACE TO RESTART", True, WHITE)
            self.game_surface.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 50))
        elif self.state == "PAUSE":
            t = self.font_large.render("PAUSED", True, YELLOW)
            self.game_surface.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))

        # UI Score / Lives
        hearts = "\u2665 " * max(self.lives, 0)
        hud_text = self.font_small.render(
            f"Level: {self.level}   Score: {self.score}   {hearts}Lives: {self.lives}",
            True, WHITE
        )
        self.game_surface.blit(hud_text, (10, 10))

        # Red flash overlay on life loss
        if getattr(self, "_flash_frames", 0) > 0:
            flash = pygame.Surface((WIDTH, HEIGHT))
            flash.set_alpha(120)
            flash.fill((220, 0, 0))
            self.game_surface.blit(flash, (0, 0))
            self._flash_frames -= 1

        # Scale game_surface to fit screen while maintaining aspect ratio
        current_w, current_h = self.screen.get_size()
        aspect_ratio = WIDTH / HEIGHT
        if current_w / current_h > aspect_ratio:
            new_h = current_h
            new_w = int(aspect_ratio * new_h)
        else:
            new_w = current_w
            new_h = int(new_w / aspect_ratio)

        scaled_surface = pygame.transform.scale(self.game_surface, (new_w, new_h))
        self.screen.fill(BLACK)
        self.screen.blit(scaled_surface, ((current_w - new_w) // 2, (current_h - new_h) // 2))

        pygame.display.flip()

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.step()
            self.draw()

if __name__ == "__main__":
    b = Montezuma()
    b.run()

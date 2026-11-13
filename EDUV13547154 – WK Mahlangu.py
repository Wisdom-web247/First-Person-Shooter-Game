import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import os
import json
import wave
import struct
import random
from collections import deque

# =====================================================================
# 1. ASSET GENERATOR
# =====================================================================
def generate_assets():
    """Generates all textures, lobby images, and sounds if missing."""
    print("Checking and generating game assets...")
    
    # 1. Container Texture
    if not os.path.exists("container.png"):
        surf = pygame.Surface((128, 128))
        surf.fill((40, 70, 110)) # Base Industrial Blue
        for i in range(0, 128, 16):
            pygame.draw.line(surf, (20, 40, 70), (i, 0), (i, 128), 4) # Shadow
            pygame.draw.line(surf, (60, 90, 140), (i+4, 0), (i+4, 128), 4) # Highlight
        pygame.draw.rect(surf, (220, 220, 220), (32, 40, 64, 30))
        pygame.image.save(surf, "container.png")

    # 2. Concrete Floor
    if not os.path.exists("floor.png"):
        surf = pygame.Surface((128, 128))
        surf.fill((60, 60, 65))
        for _ in range(1000): # Noise texture
            x, y = random.randint(0, 127), random.randint(0, 127)
            c = random.randint(40, 80)
            surf.set_at((x, y), (c, c, c))
        pygame.image.save(surf, "floor.png")

    # 3. Enemy Texture
    if not os.path.exists("enemy.png"):
        surf = pygame.Surface((64, 64))
        surf.fill((20, 20, 20))
        pygame.draw.polygon(surf, (255, 50, 50), [(32, 10), (54, 54), (10, 54)])
        pygame.image.save(surf, "enemy.png")

    # 4. Forward-facing HUD gun cutout
    gun_source = "gun.jpeg"
    gun_hud = "gun_hud.png"
    if os.path.exists(gun_source) and (
        not os.path.exists(gun_hud)
        or os.path.getmtime(gun_source) > os.path.getmtime(gun_hud)
    ):
        source = pygame.image.load(gun_source)
        scale_x = source.get_width() / 2048
        scale_y = source.get_height() / 2048
        crop_rect = pygame.Rect(
            round(620 * scale_x),
            round(520 * scale_y),
            round(820 * scale_x),
            round(1180 * scale_y),
        )
        crop = source.subsurface(crop_rect).copy()
        source_points = (
            (910, 585), (1102, 585), (1115, 790), (1175, 820),
            (1190, 980), (1240, 1110), (1280, 1300), (1330, 1530),
            (1370, 1695), (680, 1695), (720, 1530), (770, 1300),
            (810, 1110), (850, 980), (875, 820), (910, 790),
        )
        points = [
            (
                round(x * scale_x) - crop_rect.x,
                round(y * scale_y) - crop_rect.y,
            )
            for x, y in source_points
        ]
        mask = pygame.Surface(crop.get_size(), pygame.SRCALPHA, 32)
        pygame.draw.polygon(mask, (255, 255, 255, 255), points)
        weapon = pygame.Surface(crop.get_size(), pygame.SRCALPHA, 32)
        weapon.blit(crop, (0, 0))
        weapon.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.image.save(weapon, gun_hud)
    elif not os.path.exists(gun_hud):
        weapon = pygame.Surface((220, 360), pygame.SRCALPHA)
        pygame.draw.rect(weapon, (70, 75, 82), (80, 10, 60, 250))
        pygame.draw.rect(weapon, (35, 40, 48), (54, 220, 112, 140))
        pygame.draw.circle(weapon, (0, 220, 255), (110, 30), 12)
        pygame.image.save(weapon, gun_hud)

    # 5. LOBBY BACKGROUND IMAGE
    if not os.path.exists("lobby_bg.png"):
        surf = pygame.Surface((1024, 768))
        surf.fill((10, 15, 25))
        # Draw a synthetic grid for the lobby
        for i in range(0, 1024, 64):
            pygame.draw.line(surf, (0, 50, 100), (i, 0), (i, 768))
        for i in range(0, 768, 64):
            pygame.draw.line(surf, (0, 50, 100), (0, i), (1024, i))
        pygame.image.save(surf, "lobby_bg.png")

    # Audio Generation
    if not os.path.exists("lobby_music.wav"):
        with wave.open("lobby_music.wav", "w") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100)
            for i in range(44100 * 2):
                f.writeframesraw(struct.pack("<h", int(math.sin(i * 0.01) * 6000)))
    if not os.path.exists("game_music.wav"):
        with wave.open("game_music.wav", "w") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100)
            for i in range(44100 * 1):
                f.writeframesraw(struct.pack("<h", int(math.sin(i * 0.05) * 10000)))
    if not os.path.exists("gunshot.wav"):
        sample_rate = 44100
        with wave.open("gunshot.wav", "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            frames = bytearray()
            for i in range(int(sample_rate * 0.18)):
                t = i / sample_rate
                envelope = math.exp(-t * 32.0)
                crack = random.uniform(-1.0, 1.0) * math.exp(-t * 65.0) * 0.8
                boom = math.sin(2.0 * math.pi * 85.0 * t) * envelope * 0.55
                sample = max(-1.0, min(1.0, crack + boom))
                frames.extend(struct.pack("<h", int(sample * 32767)))
            f.writeframes(frames)

# =====================================================================
# 2. WORLD DATA (ENLARGED) & 3D ENGINE
# =====================================================================
LEVEL_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,1,1,1,0,1,0,1,1,1,0,1,0,1,1,1,0,1,0,1,1,1,0,1],
    [1,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,1],
    [1,0,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1],
    [1,0,0,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,0,0,1],
    [1,0,1,1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,1,1,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
]
BLOCK_SIZE = 3.0
PLAYER_PADDING = 0.8
CONTAINER_STANDING_HEIGHT = BLOCK_SIZE * 2.0
MAP_OFFSET_X = ((len(LEVEL_MAP[0]) - 1) / 2.0) * BLOCK_SIZE
MAP_OFFSET_Z = ((len(LEVEL_MAP) - 1) / 2.0) * BLOCK_SIZE
JUMP_VELOCITY = 0.8
GRAVITY = 0.045

CUBE_VERTICES = ((1,-1,-1), (1,1,-1), (-1,1,-1), (-1,-1,-1), (1,-1,1), (1,1,1), (-1,-1,1), (-1,1,1))
CUBE_FACES = ((0,1,2,3), (3,2,7,6), (6,7,5,4), (4,5,1,0), (1,5,7,2), (4,0,3,6))
TEX_COORDS = ((0,0), (1,0), (1,1), (0,1))
# Normals allow OpenGL to calculate lighting (Ray-tracing lite)
NORMALS = ((0,0,-1), (-1,0,0), (0,0,1), (1,0,0), (0,1,0), (0,-1,0))

def load_texture(filename):
    surf = pygame.image.load(filename)
    data = pygame.image.tobytes(surf, "RGBA", True)
    w, h = surf.get_rect().size
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return tex

def draw_cube(x, y, z, tex_id, size=1.0, scale_y=1.0):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(size, size * scale_y, size)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glBegin(GL_QUADS)
    for f_idx, face in enumerate(CUBE_FACES):
        glNormal3fv(NORMALS[f_idx]) # Apply lighting normal
        for i, vertex in enumerate(face):
            glTexCoord2fv(TEX_COORDS[i])
            glVertex3fv(CUBE_VERTICES[vertex])
    glEnd()
    glPopMatrix()

def draw_floor(tex_id):
    glPushMatrix()
    glTranslatef(0, -BLOCK_SIZE, 0)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-100, 0, -100)
    glTexCoord2f(30, 0); glVertex3f(100, 0, -100)
    glTexCoord2f(30, 30); glVertex3f(100, 0, 100)
    glTexCoord2f(0, 30); glVertex3f(-100, 0, 100)
    glEnd()
    glPopMatrix()

def check_collision(x, z, padding=PLAYER_PADDING, player_y=0.0):
    pts = [(x+padding, z+padding), (x-padding, z-padding), (x+padding, z-padding), (x-padding, z+padding)]
    for px, pz in pts:
        col = int((px + MAP_OFFSET_X + (BLOCK_SIZE/2)) // BLOCK_SIZE)
        row = int((pz + MAP_OFFSET_Z + (BLOCK_SIZE/2)) // BLOCK_SIZE)
        if row < 0 or row >= len(LEVEL_MAP) or col < 0 or col >= len(LEVEL_MAP[0]): return True
        if LEVEL_MAP[row][col] == 1 and player_y < CONTAINER_STANDING_HEIGHT: return True
    return False

def get_ground_height(x, z):
    points = (
        (x + PLAYER_PADDING, z + PLAYER_PADDING),
        (x - PLAYER_PADDING, z - PLAYER_PADDING),
        (x + PLAYER_PADDING, z - PLAYER_PADDING),
        (x - PLAYER_PADDING, z + PLAYER_PADDING),
    )
    ground_height = 0.0
    for px, pz in points:
        col = int((px + MAP_OFFSET_X + (BLOCK_SIZE/2)) // BLOCK_SIZE)
        row = int((pz + MAP_OFFSET_Z + (BLOCK_SIZE/2)) // BLOCK_SIZE)
        if 0 <= row < len(LEVEL_MAP) and 0 <= col < len(LEVEL_MAP[0]) and LEVEL_MAP[row][col] == 1:
            ground_height = CONTAINER_STANDING_HEIGHT
    return ground_height

def find_enemy_spawn(cam_x, cam_z, enemies, exclude=None):
    candidates = []
    for row, tiles in enumerate(LEVEL_MAP):
        for col, tile in enumerate(tiles):
            if tile != 0:
                continue
            spawn_x = col * BLOCK_SIZE - MAP_OFFSET_X
            spawn_z = row * BLOCK_SIZE - MAP_OFFSET_Z
            player_dist = math.hypot(spawn_x - cam_x, spawn_z - cam_z)
            enemy_dist = min(
                (
                    math.hypot(spawn_x - enemy["x"], spawn_z - enemy["z"])
                    for enemy in enemies
                    if enemy is not exclude
                ),
                default=float("inf"),
            )
            if player_dist >= 12.0 and enemy_dist >= 2.0:
                candidates.append((spawn_x, spawn_z))
    if not candidates:
        raise RuntimeError("No safe floor tile is available for an enemy spawn.")
    return random.choice(candidates)


def world_to_grid_cell(x, z):
    col = int((x + MAP_OFFSET_X + (BLOCK_SIZE / 2)) // BLOCK_SIZE)
    row = int((z + MAP_OFFSET_Z + (BLOCK_SIZE / 2)) // BLOCK_SIZE)
    return row, col


def build_enemy_distance_map(cam_x, cam_z):
    target_cell = world_to_grid_cell(cam_x, cam_z)
    target_row, target_col = target_cell
    if (
        target_row < 0 or target_row >= len(LEVEL_MAP)
        or target_col < 0 or target_col >= len(LEVEL_MAP[0])
        or LEVEL_MAP[target_row][target_col] != 0
    ):
        floor_cells = (
            (row, col)
            for row, tiles in enumerate(LEVEL_MAP)
            for col, tile in enumerate(tiles)
            if tile == 0
        )
        target_cell = min(
            floor_cells,
            key=lambda cell: math.hypot(
                cell[1] * BLOCK_SIZE - MAP_OFFSET_X - cam_x,
                cell[0] * BLOCK_SIZE - MAP_OFFSET_Z - cam_z,
            ),
        )

    distances = {target_cell: 0}
    frontier = deque([target_cell])
    while frontier:
        row, col = frontier.popleft()
        next_distance = distances[(row, col)] + 1
        for next_row, next_col in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ):
            if (
                0 <= next_row < len(LEVEL_MAP)
                and 0 <= next_col < len(LEVEL_MAP[0])
                and LEVEL_MAP[next_row][next_col] == 0
                and (next_row, next_col) not in distances
            ):
                distances[(next_row, next_col)] = next_distance
                frontier.append((next_row, next_col))
    return target_cell, distances


def next_enemy_cell(enemy_x, enemy_z, distances):
    row, col = world_to_grid_cell(enemy_x, enemy_z)
    current_cell = (row, col)
    current_distance = distances.get(current_cell)
    if current_distance is None:
        return None
    if current_distance == 0:
        return current_cell

    for next_cell in (
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ):
        if distances.get(next_cell) == current_distance - 1:
            return next_cell
    return None


def format_clock(seconds):
    if seconds is None:
        return "--:--"
    total_seconds = max(0, int(math.ceil(seconds)))
    return f"{total_seconds // 60:02}:{total_seconds % 60:02}"


# =====================================================================
# 3. 2D UI & HUD RENDERER
# =====================================================================
def render_2d_ui(
    display_w, display_h, state, kills, target_kills, high_score, gun_img,
    is_shooting, lobby_img, tod, time_left, hard_completions,
    best_hard_time, timed_out, difficulty,
):
    ui_surface = pygame.Surface((display_w, display_h), pygame.SRCALPHA)
    font_large = pygame.font.SysFont("Courier", 54, bold=True)
    font_med = pygame.font.SysFont("Courier", 32, bold=True)
    font_small = pygame.font.SysFont("Courier", 24)
    font_record = pygame.font.SysFont("Courier", 18, bold=True)

    if state == "MENU":
        ui_surface.blit(lobby_img, (0, 0))
        t1 = font_large.render("HARBOUR ASSAULT", True, (255, 200, 50))
        t2 = font_med.render(f"HIGH SCORE (KILLS): {high_score}", True, (0, 255, 255))
        t3 = font_small.render(f"SCENERY/TIME OF DAY: {tod} (Press 'T' to change)", True, (255, 150, 150))
        t4 = font_small.render("SELECT DIFFICULTY TO START:", True, (255, 255, 255))
        t5 = font_med.render("[1] EASY   [2] MEDIUM   [3] HARD (500 Kills)", True, (0, 255, 0))
        t6 = font_small.render("NUMPAD 1-3 ALSO SELECTS MODES (NUM LOCK ON)", True, (255, 255, 255))
        t7 = font_small.render("WASD: MOVE   MOUSE: AIM   LEFT CLICK: FIRE   SPACE: JUMP", True, (0, 255, 255))
        
        ui_surface.blit(t1, (display_w//2 - t1.get_width()//2, display_h//5))
        ui_surface.blit(t2, (display_w//2 - t2.get_width()//2, display_h//5 + 70))
        ui_surface.blit(t3, (display_w//2 - t3.get_width()//2, display_h//2 - 40))
        ui_surface.blit(t4, (display_w//2 - t4.get_width()//2, display_h//2 + 40))
        ui_surface.blit(t5, (display_w//2 - t5.get_width()//2, display_h//2 + 80))
        ui_surface.blit(t6, (display_w//2 - t6.get_width()//2, display_h//2 + 130))
        ui_surface.blit(t7, (display_w//2 - t7.get_width()//2, display_h//2 + 165))

        record_rect = pygame.Rect(display_w - 350, display_h - 145, 330, 125)
        pygame.draw.rect(ui_surface, (0, 20, 45, 220), record_rect, border_radius=10)
        pygame.draw.rect(ui_surface, (0, 210, 255, 255), record_rect, 2, border_radius=10)
        record_lines = (
            f"HARD CLEARS: {hard_completions}",
            f"BEST TIME: {format_clock(best_hard_time)}",
        )
        ui_surface.blit(font_record.render("HARD HIGH SCORE", True, (255, 200, 50)),
                        (record_rect.x + 14, record_rect.y + 16))
        for index, line in enumerate(record_lines):
            ui_surface.blit(font_record.render(line, True, (220, 245, 255)),
                            (record_rect.x + 14, record_rect.y + 48 + index * 27))

    elif state in ["GAMEOVER", "VICTORY"]:
        color = (50, 0, 0, 200) if state == "GAMEOVER" else (0, 50, 0, 200)
        ui_surface.fill(color)
        msg = ("TIME EXPIRED" if timed_out else "GAME OVER") if state == "GAMEOVER" else "DOCKYARD CLEARED!"
        t1 = font_large.render(msg, True, (255, 255, 255))
        t2 = font_med.render(f"TOTAL KILLS: {kills}", True, (255, 255, 255))

        ui_surface.blit(t1, (display_w//2 - t1.get_width()//2, display_h//3))
        ui_surface.blit(t2, (display_w//2 - t2.get_width()//2, display_h//3 + 60))
        if state == "VICTORY":
            next_difficulty = difficulty + 1 if difficulty < 3 else 1
            next_name = ("EASY", "MEDIUM", "HARD")[next_difficulty - 1]
            prompts = (
                f"Press [N] for {next_name}",
                "Press [R] to Replay This Stage",
                "Press [M] for Main Menu",
            )
        else:
            prompts = (
                "Press [R] to Restart Current Difficulty",
                "Press [M] for Main Menu",
            )
        for index, prompt in enumerate(prompts):
            text = font_small.render(prompt, True, (200, 200, 200))
            ui_surface.blit(text, (display_w//2 - text.get_width()//2,
                                   display_h//2 + 20 + index * 40))

    elif state == "PLAYING":
        gun_x = (display_w - gun_img.get_width()) // 2
        gun_y = display_h // 2 - int(gun_img.get_height() * 0.115)
        if is_shooting > 0:
            gun_x += 10
            gun_y += 14
        ui_surface.blit(gun_img, (gun_x, gun_y))

        cx, cy = display_w//2, display_h//2
        color = (255,0,0) if is_shooting > 0 else (0,255,255)
        pygame.draw.line(ui_surface, color, (cx-12, cy), (cx+12, cy), 2)
        pygame.draw.line(ui_surface, color, (cx, cy-12), (cx, cy+12), 2)

        sc_txt = font_med.render(f"KILLS: {kills} / {target_kills}", True, (0, 255, 255))
        ui_surface.blit(sc_txt, (20, 20))
        timer_txt = font_med.render(f"TIME: {format_clock(time_left)}", True, (255, 220, 80))
        ui_surface.blit(timer_txt, (display_w - timer_txt.get_width() - 20, 20))

    # Push to OpenGL
    data = pygame.image.tobytes(ui_surface, "RGBA", False)
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, display_w, display_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, display_w, display_h, 0)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1, 1, 1, 1)
    
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(0, 0)
    glTexCoord2f(1, 0); glVertex2f(display_w, 0)
    glTexCoord2f(1, 1); glVertex2f(display_w, display_h)
    glTexCoord2f(0, 1); glVertex2f(0, display_h)
    glEnd()

    glDisable(GL_BLEND)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glDeleteTextures([tex_id])

# =====================================================================
# 4. MAIN GAME ENGINE
# =====================================================================
def main():
    pygame.init()
    pygame.mixer.init()
    generate_assets()
    
    display_w, display_h = 1024, 768
    pygame.display.set_mode((display_w, display_h), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Harbour Assault - Dynamic Environment")

    glEnable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)
    
    # Textures
    container_tex = load_texture("container.png")
    floor_tex = load_texture("floor.png")
    enemy_tex = load_texture("enemy.png")
    gun_img = pygame.image.load("gun_hud.png").convert_alpha()
    gun_img = pygame.transform.smoothscale(gun_img, (320, 460))
    lobby_img = pygame.transform.smoothscale(
        pygame.image.load("lobby_bg.png").convert(), (display_w, display_h)
    )
    gunshot_sound = pygame.mixer.Sound("gunshot.wav")
    gunshot_sound.set_volume(0.8)

    # Time of Day Settings (Lighting, Sky Color, Fog Density)
    tod_profiles = {
        "DAY": {"sky": (0.5, 0.7, 1.0, 1.0), "fog": 0.015, "light": (1.0, 1.0, 0.9, 1.0)},
        "AFTERNOON": {"sky": (0.8, 0.4, 0.2, 1.0), "fog": 0.02, "light": (1.0, 0.6, 0.3, 1.0)},
        "NIGHT": {"sky": (0.02, 0.02, 0.05, 1.0), "fog": 0.04, "light": (0.2, 0.2, 0.4, 1.0)}
    }
    current_tod_idx = 0
    tods = ["DAY", "AFTERNOON", "NIGHT"]

    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, (display_w / display_h), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    state = "MENU"
    high_score = 0
    records_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hard_records.json")
    hard_completions = 0
    best_hard_time = None
    if os.path.exists(records_path):
        with open(records_path, "r", encoding="utf-8") as records_file:
            saved_records = json.load(records_file)
        if not isinstance(saved_records, dict):
            raise ValueError("Hard completion records must be a JSON object.")
        hard_completions = saved_records["hard_completions"]
        best_hard_time = saved_records["best_hard_time_seconds"]
        if not isinstance(hard_completions, int) or hard_completions < 0:
            raise ValueError("Hard completion count must be a non-negative integer.")
        if best_hard_time is not None and (
            not isinstance(best_hard_time, (int, float)) or best_hard_time < 0
        ):
            raise ValueError("Best Hard completion time must be a non-negative number.")
    kills = 0
    target_kills = 0
    difficulty = 1
    stage_duration = 90.0
    stage_started_at = 0
    time_left = stage_duration
    timed_out = False
    
    cam_x, cam_z = 0.0, 0.0
    cam_y = 0.0
    jump_velocity = 0.0
    is_grounded = True
    yaw, pitch = 0.0, 0.0
    
    enemies = []
    enemy_speed = 0.03
    base_enemy_speed = enemy_speed
    enemy_count = 3
    enemy_spawn_interval = 8000
    next_enemy_spawn_at = 0
    is_shooting = 0
    current_music = ""
    max_enemies = 30

    clock = pygame.time.Clock()
    running = True

    def setup_game(diff):
        nonlocal kills, cam_x, cam_y, cam_z, jump_velocity, is_grounded, yaw, pitch
        nonlocal enemies, enemy_speed, base_enemy_speed, enemy_count, target_kills, difficulty
        nonlocal stage_duration, stage_started_at, time_left, timed_out
        nonlocal enemy_spawn_interval, next_enemy_spawn_at
        difficulty = diff
        kills = 0
        cam_x, cam_y, cam_z, jump_velocity, is_grounded, yaw, pitch = 0.0, 0.0, 0.0, 0.0, True, 0.0, 0.0
        enemies.clear()
        stage_duration = 120.0 if diff == 3 else 90.0
        stage_started_at = pygame.time.get_ticks()
        time_left = stage_duration
        timed_out = False
        
        if diff == 1: # Easy
            enemy_speed = 0.03
            enemy_count = 5
            target_kills = 30
            enemy_spawn_interval = 7000
        elif diff == 2: # Medium
            enemy_speed = 0.05
            enemy_count = 10
            target_kills = 100
            enemy_spawn_interval = 6000
        elif diff == 3: # Hard
            enemy_speed = 0.07
            enemy_count = 20
            target_kills = 500
            enemy_spawn_interval = 5000

        base_enemy_speed = enemy_speed
        for _ in range(enemy_count): spawn_enemy()
        next_enemy_spawn_at = pygame.time.get_ticks() + enemy_spawn_interval
            
        pygame.mouse.get_rel() 

    def update_stage_timer():
        nonlocal time_left, timed_out, state
        if state != "PLAYING":
            return
        elapsed = (pygame.time.get_ticks() - stage_started_at) / 1000.0
        time_left = max(0.0, stage_duration - elapsed)
        if time_left <= 0.0:
            timed_out = True
            state = "GAMEOVER"

    def record_hard_completion(completion_time):
        nonlocal hard_completions, best_hard_time
        hard_completions += 1
        if best_hard_time is None or completion_time < best_hard_time:
            best_hard_time = completion_time
        temp_records_path = records_path + ".tmp"
        with open(temp_records_path, "w", encoding="utf-8") as records_file:
            json.dump({
                "hard_completions": hard_completions,
                "best_hard_time_seconds": best_hard_time,
            }, records_file, indent=2)
        os.replace(temp_records_path, records_path)

    def spawn_enemy():
        spawn_x, spawn_z = find_enemy_spawn(cam_x, cam_z, enemies)
        enemies.append({"x": spawn_x, "z": spawn_z})

    def apply_environment(tod_name):
        """Applies Fog and OpenGL Light simulation to match time of day"""
        p = tod_profiles[tod_name]
        glClearColor(*p["sky"])
        
        # Fog Setup
        glEnable(GL_FOG)
        glFogfv(GL_FOG_COLOR, p["sky"])
        glFogf(GL_FOG_DENSITY, p["fog"])
        
        # Lighting Setup
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        glLightfv(GL_LIGHT0, GL_DIFFUSE, p["light"])
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
        glLightfv(GL_LIGHT0, GL_POSITION, (10, 50, 10, 0)) # Directional light from above

    while running:
        update_stage_timer()
        tod_name = tods[current_tod_idx]
        
        for event in pygame.event.get():
            update_stage_timer()
            if event.type == QUIT: running = False
                
            if state == "MENU":
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE: running = False
                    if event.key == K_t: current_tod_idx = (current_tod_idx + 1) % 3
                    if event.key in (K_1, K_KP1): state = "PLAYING"; setup_game(1)
                    if event.key in (K_2, K_KP2): state = "PLAYING"; setup_game(2)
                    if event.key in (K_3, K_KP3): state = "PLAYING"; setup_game(3)
            
            elif state in ["GAMEOVER", "VICTORY"]:
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE: running = False
                    if event.key == K_m: state = "MENU"
                    if event.key == K_r:
                        state = "PLAYING"; setup_game(difficulty)
                    if event.key == K_n and state == "VICTORY":
                        next_difficulty = difficulty + 1 if difficulty < 3 else 1
                        state = "PLAYING"; setup_game(next_difficulty)
                        
            elif state == "PLAYING":
                if event.type == KEYDOWN and event.key == K_ESCAPE: state = "MENU"
                if event.type == KEYDOWN and event.key == K_SPACE and is_grounded:
                    jump_velocity = JUMP_VELOCITY
                    is_grounded = False
                    
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    is_shooting = 10
                    gunshot_sound.play()
                    # Raycast Hit Detection
                    y_rad, p_rad = math.radians(yaw), math.radians(pitch)
                    fx, fy, fz = math.sin(y_rad)*math.cos(p_rad), -math.sin(p_rad), -math.cos(y_rad)*math.cos(p_rad)
                    
                    for e in enemies:
                        vx, vy, vz = e["x"] - cam_x, -cam_y, e["z"] - cam_z
                        dist = math.sqrt(vx*vx + vy*vy + vz*vz)
                        if 0 < dist < 20.0:
                            dot = (fx*(vx/dist)) + (fy*(vy/dist)) + (fz*(vz/dist))
                            if dot > 0.94: # Direct hit
                                kills += 1
                                if kills > high_score: high_score = kills
                                
                                enemy_speed = min(
                                    enemy_speed + base_enemy_speed * 0.02,
                                    base_enemy_speed * 2.0,
                                )
                                if kills % 2 == 0 and len(enemies) < max_enemies:
                                    spawn_enemy()
                                
                                # Respawn killed enemy far away
                                e["x"], e["z"] = find_enemy_spawn(cam_x, cam_z, enemies, e)
                                
                                if kills >= target_kills:
                                    elapsed = (pygame.time.get_ticks() - stage_started_at) / 1000.0
                                    time_left = max(0.0, stage_duration - elapsed)
                                    if difficulty == 3:
                                        record_hard_completion(elapsed)
                                    state = "VICTORY"
                                break

        update_stage_timer()
        desired_music = "game" if state == "PLAYING" else "lobby"
        if current_music != desired_music:
            music_file = "game_music.wav" if desired_music == "game" else "lobby_music.wav"
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.play(-1)
            current_music = desired_music

        is_playing = state == "PLAYING"
        pygame.mouse.set_visible(not is_playing)
        pygame.event.set_grab(is_playing)

        if state == "PLAYING":
            if is_shooting > 0: is_shooting -= 1
            now = pygame.time.get_ticks()
            if len(enemies) < max_enemies and now >= next_enemy_spawn_at:
                spawn_enemy()
                next_enemy_spawn_at = now + enemy_spawn_interval

            mouse_dx, mouse_dy = pygame.mouse.get_rel()
            yaw += mouse_dx * 0.15
            pitch = max(-89.0, min(89.0, pitch + mouse_dy * 0.15))

            keys = pygame.key.get_pressed()
            yaw_rad = math.radians(yaw)
            dx, dz = math.sin(yaw_rad) * 0.22, -math.cos(yaw_rad) * 0.22
            rx, rz = math.cos(yaw_rad) * 0.22, math.sin(yaw_rad) * 0.22

            new_x, new_z = cam_x, cam_z
            if keys[K_w]: new_x += dx; new_z += dz
            if keys[K_s]: new_x -= dx; new_z -= dz
            if keys[K_a]: new_x -= rx; new_z -= rz
            if keys[K_d]: new_x += rx; new_z += rz

            if not check_collision(new_x, cam_z, player_y=cam_y): cam_x = new_x
            if not check_collision(cam_x, new_z, player_y=cam_y): cam_z = new_z

            ground_y = get_ground_height(cam_x, cam_z)
            if is_grounded and cam_y > ground_y:
                is_grounded = False
            if not is_grounded:
                cam_y += jump_velocity
                jump_velocity -= GRAVITY
                ground_y = get_ground_height(cam_x, cam_z)
                if cam_y <= ground_y:
                    cam_y = ground_y
                    jump_velocity = 0.0
                    is_grounded = True

            target_cell, enemy_distances = build_enemy_distance_map(cam_x, cam_z)
            for e in enemies:
                dir_x, dir_z = cam_x - e["x"], cam_z - e["z"]
                dist = math.sqrt(dir_x**2 + dir_z**2)
                player_dist = math.sqrt(dist**2 + cam_y**2)
                
                if player_dist < 1.5: 
                    state = "GAMEOVER"
                    pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                    continue

                current_cell = world_to_grid_cell(e["x"], e["z"])
                next_cell = next_enemy_cell(e["x"], e["z"], enemy_distances)
                if next_cell is None:
                    continue
                if next_cell == target_cell:
                    target_x, target_z = cam_x, cam_z
                else:
                    target_x = next_cell[1] * BLOCK_SIZE - MAP_OFFSET_X
                    target_z = next_cell[0] * BLOCK_SIZE - MAP_OFFSET_Z

                move_x, move_z = target_x - e["x"], target_z - e["z"]
                move_distance = math.hypot(move_x, move_z)
                if move_distance > 0:
                    step = min(enemy_speed, move_distance)
                    next_x = e["x"] + move_x / move_distance * step
                    next_z = e["z"] + move_z / move_distance * step
                    if not check_collision(next_x, next_z):
                        e["x"], e["z"] = next_x, next_z
                    elif current_cell != next_cell:
                        if abs(move_x) >= abs(move_z):
                            if not check_collision(next_x, e["z"]):
                                e["x"] = next_x
                            if not check_collision(e["x"], next_z):
                                e["z"] = next_z
                        else:
                            if not check_collision(e["x"], next_z):
                                e["z"] = next_z
                            if not check_collision(next_x, e["z"]):
                                e["x"] = next_x

        # --- 3D RENDERING ---
        apply_environment(tod_name)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if state in ["PLAYING", "GAMEOVER", "VICTORY"]:
            glLoadIdentity()
            glRotatef(pitch, 1, 0, 0)
            glRotatef(yaw, 0, 1, 0)
            glTranslatef(-cam_x, -cam_y, -cam_z)

            draw_floor(floor_tex)

            for r in range(len(LEVEL_MAP)):
                for c in range(len(LEVEL_MAP[r])):
                    if LEVEL_MAP[r][c] == 1:
                        draw_cube((c*BLOCK_SIZE)-MAP_OFFSET_X, 0.0, (r*BLOCK_SIZE)-MAP_OFFSET_Z, container_tex, size=BLOCK_SIZE/2, scale_y=2.0)

            ticks = pygame.time.get_ticks()
            for e in enemies:
                distance = math.hypot(e["x"] - cam_x, e["z"] - cam_z)
                if distance < 12.0:
                    flash_interval = 300 if distance >= 6.0 else 120
                    if (ticks // flash_interval) % 2 == 0:
                        glColor3f(1.0, 0.2, 0.2)
                    else:
                        glColor3f(0.15, 0.15, 0.15)
                else:
                    glColor3f(1.0, 1.0, 1.0)
                draw_cube(e["x"], 0.0, e["z"], enemy_tex, size=0.8)
            glColor3f(1.0, 1.0, 1.0)

        # Disable 3D Lighting/Fog before drawing 2D HUD
        glDisable(GL_LIGHTING); glDisable(GL_FOG)
        glDisable(GL_DEPTH_TEST)
        
        render_2d_ui(
            display_w, display_h, state, kills, target_kills, high_score, gun_img,
            is_shooting, lobby_img, tod_name, time_left, hard_completions,
            best_hard_time, timed_out, difficulty,
        )
        glEnable(GL_DEPTH_TEST)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
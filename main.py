import pygame
import sys
import random
import asyncio
from pathlib import Path

# import helpers (now provide init_audio_once + warmup_sfx)
try:
    from sound_effects import (
        init_audio_once,
        init_sounds,
        warmup_sfx,
        play_background,
        play_jump,
        play_crash,
        jump_sound,
        crash_sound,
        wake_audio_context,
    )
except Exception as e:
    print("sound_effects import failed:", e)

    def init_audio_once(sample_rate=24000, channels=1, buffer=256):
        pass

    def init_sounds():
        pass

    def warmup_sfx():
        pass

    def play_background():
        pass

    def play_jump():
        pass

    def play_crash():
        pass
    
    def wake_audio_context():
        pass
    
    jump_sound = None
    crash_sound = None


# Game Variables
GAME_WIDTH = 360
GAME_HEIGHT = 640

# Check if running in web browser
IS_WEB = sys.platform == "emscripten"
ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
SOUNDS = ROOT / "sounds"

# bird class
bird_x = GAME_WIDTH / 8
bird_y = GAME_HEIGHT / 2
bird_width = 34  # 17/12
bird_height = 24

# Pipe class
pipe_x = GAME_WIDTH
pipe_y = 0
pipe_width = 64
pipe_height = 512


class Bird(pygame.Rect):
    def __init__(self, img):
        pygame.Rect.__init__(self, bird_x, bird_y, bird_width, bird_height)
        self.img = img


class Pipe(pygame.Rect):
    def __init__(self, img):
        pygame.Rect.__init__(self, pipe_x, pipe_y, pipe_width, pipe_height)
        self.img = img
        self.passed = False


async def main():
    global bird, pipes, velocity_x, velocity_y, gravity, score, game_over, window, clock

    # Web: don't pre-init mixer at boot (can block/autoplay-gate); desktop is fine.
    if not IS_WEB:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)

    pygame.init()
    print("PYGAME INIT OK, IS_WEB =", IS_WEB)
    print("ASSETS exists:", ASSETS.exists())
    if ASSETS.exists():
        print("ASSETS files:", [p.name for p in ASSETS.iterdir()])

    # Simple display mode for web compatibility
    flags = 0 if IS_WEB else (pygame.SCALED | pygame.RESIZABLE)
    window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), flags)
    print("Display mode set successfully")

    # Set pixelated rendering for web
    if IS_WEB:
        import platform

        platform.window.canvas.style.imageRendering = "pixelated"

    pygame.display.set_caption("Flappy Bird")
    clock = pygame.time.Clock()

    # Load font
    try:
        font = pygame.font.Font(str(ASSETS / "PressStart2P.ttf"), 20)
        font_small = pygame.font.Font(str(ASSETS / "PressStart2P.ttf"), 12)
        print("Font loaded successfully")
    except Exception as e:
        print(f"Font failed, using default: {e}")
        font = pygame.font.Font(None, 35)
        font_small = pygame.font.Font(None, 25)

    # Load images AFTER set_mode - this is critical for web!
    def load_image_safe(path, use_alpha=True):
        try:
            img = pygame.image.load(str(path))
            if use_alpha:
                return img.convert_alpha()
            else:
                return img.convert()
        except Exception as e:
            print(f"Failed to load {path}: {e}")
            # Return a colored rectangle as fallback
            surf = pygame.Surface((64, 64))
            if "bird" in str(path):
                surf.fill((255, 255, 0))  # Yellow for bird
            elif "pipe" in str(path):
                surf.fill((0, 255, 0))  # Green for pipes
            elif "bg" in str(path):
                surf.fill((135, 206, 235))  # Sky blue for background
            else:
                surf.fill((255, 0, 255))  # Magenta for other
            return surf

    # Load all images - now using Path objects
    background_image = load_image_safe(ASSETS / "flappybirdbg.png", False)
    background_image = pygame.transform.scale(
        background_image, (GAME_WIDTH, GAME_HEIGHT)
    )

    bird_image = load_image_safe(ASSETS / "flappybird.png", True)
    bird_image = pygame.transform.scale(bird_image, (bird_width, bird_height))

    top_pipe_image = load_image_safe(ASSETS / "toppipe.png", True)
    top_pipe_image = pygame.transform.scale(top_pipe_image, (pipe_width, pipe_height))

    bottom_pipe_image = load_image_safe(ASSETS / "bottompipe.png", True)
    bottom_pipe_image = pygame.transform.scale(
        bottom_pipe_image, (pipe_width, pipe_height)
    )

    emoji_image = load_image_safe(ASSETS / "score.png", True)
    emoji_image = pygame.transform.scale(emoji_image, (75, 75))

    # game logic
    bird = Bird(bird_image)
    pipes = []
    velocity_x = -2  # moves pipes to the left
    velocity_y = 0  # move bird up and down
    gravity = 0.4
    score = 0
    game_over = False

    # ---- AUDIO ----
    audio_armed = IS_WEB
    audio_keep_alive_counter = 0

    def unlock_audio_if_needed():
        nonlocal audio_armed
        if not audio_armed:
            return
        audio_armed = False
        try:
            init_audio_once(sample_rate=24000, channels=1, buffer=512)
            init_sounds()
            warmup_sfx()  # decode SFX once so mobile fires instantly
            play_background()
            
            # Mobile Safari fix: play a silent sound immediately to activate context
            if jump_sound:
                v = jump_sound.get_volume()
                jump_sound.set_volume(0)
                pygame.mixer.Channel(1).play(jump_sound)
                pygame.mixer.Channel(1).stop()
                jump_sound.set_volume(v)
            
            # Debug output to verify on phone
            print("WEB AUDIO: unlocked + warmed")
            print("mixer init:", pygame.mixer.get_init())  # (freq, format, channels)
            from sound_effects import jump_sound, crash_sound
            if jump_sound:
                print(f"jump SFX: {jump_sound.get_length():.2f}s @ {jump_sound.get_num_channels()} ch")
            else:
                print("jump SFX: NOT LOADED")
            if crash_sound:
                print(f"crash SFX: {crash_sound.get_length():.2f}s @ {crash_sound.get_num_channels()} ch")
            else:
                print("crash SFX: NOT LOADED")
            print(f"Total channels: {pygame.mixer.get_num_channels()}")
        except Exception as e:
            print("WEB AUDIO unlock failed:", e)

    def draw():
        # Always draw background
        window.blit(background_image, (0, 0))

        # Draw bird
        window.blit(bird.img, bird)
        for pipe in pipes:
            window.blit(pipe.img, pipe)

        # Score display
        emoji_rect = emoji_image.get_rect(topleft=(5, 6))
        window.blit(emoji_image, emoji_rect)

        score_str = str(int(score))
        text_surf = font_small.render(score_str, True, (255, 255, 255))

        pad = 16
        inner = emoji_rect.inflate(-2 * pad, -2 * pad)
        text_rect = text_surf.get_rect(center=inner.center)
        window.blit(text_surf, text_rect)

        if game_over:
            go = font.render("Game Over", True, (255, 0, 0))
            go_rect = go.get_rect(center=(GAME_WIDTH // 2, 100))
            window.blit(go, go_rect)

            restart = font_small.render("Click/Tap to restart", True, (255, 255, 255))
            restart_rect = restart.get_rect(center=(GAME_WIDTH // 2, 140))
            window.blit(restart, restart_rect)

    def move():
        global velocity_y, score, game_over
        velocity_y += gravity
        bird.y += int(float(velocity_y))
        bird.y = max(bird.y, 0)

        if bird.y > GAME_HEIGHT:
            game_over = True
            try:
                if IS_WEB and crash_sound:
                    pygame.mixer.Channel(2).play(crash_sound)
                else:
                    play_crash()
            except Exception as e:
                print(f"Crash sound error: {e}")
            return

        for pipe in pipes:
            pipe.x += velocity_x

            if not pipe.passed and bird.x > pipe.x + pipe.width:
                score += 0.5
                pipe.passed = True

            if bird.colliderect(pipe):
                game_over = True
                try:
                    play_crash()
                except Exception as e:
                    print(f"Crash sound error: {e}")

        while len(pipes) > 0 and pipes[0].x + pipe_width < -pipe_width:
            pipes.pop(0)

    def create_pipe():
        random_pipe_y = pipe_y - pipe_height / 4 - random.random() * (pipe_height / 2)
        opening_space = GAME_HEIGHT / 4

        top_pipe = Pipe(top_pipe_image)
        top_pipe.y = int(float(random_pipe_y))
        pipes.append(top_pipe)

        bottom_pipe = Pipe(bottom_pipe_image)
        bottom_pipe.y = int(float(top_pipe.y + top_pipe.height + opening_space))
        pipes.append(bottom_pipe)

    create_pipes_timer = pygame.USEREVENT + 0
    pygame.time.set_timer(create_pipes_timer, 1500)

    # Desktop can init immediately
    if not IS_WEB:
        try:
            init_audio_once(sample_rate=24000, channels=1, buffer=512)
            init_sounds()
            warmup_sfx()
            play_background()
        except Exception as e:
            print("AUDIO INIT FAILED (desktop):", e)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                pygame.quit()
                return

            if event.type == create_pipes_timer and not game_over:
                create_pipe()

            # Handle keyboard input
            if event.type == pygame.KEYDOWN:
                if IS_WEB and audio_armed:
                    unlock_audio_if_needed()
                    # After unlock, process the jump immediately
                    if event.key in (pygame.K_SPACE, pygame.K_x, pygame.K_UP) and not game_over:
                        velocity_y = -6
                    continue

                if event.key in (pygame.K_SPACE, pygame.K_x, pygame.K_UP):
                    if not game_over:
                        velocity_y = -6
                        try:
                            play_jump()
                        except Exception as e:
                            print(f"Jump sound error: {e}")
                    else:
                        # Reset game
                        bird.y = int(float(bird_y))
                        pipes.clear()
                        score = 0
                        game_over = False
                        velocity_y = 0

            # Handle touch/mouse input
            if event.type == pygame.MOUSEBUTTONDOWN:
                if IS_WEB and audio_armed:
                    unlock_audio_if_needed()
                    # After unlock, process the jump immediately
                    if not game_over:
                        velocity_y = -6
                    continue

                if not game_over:
                    velocity_y = -6
                    try:
                        # Force immediate playback for mobile
                        if IS_WEB:
                            pygame.mixer.Channel(1).play(jump_sound) if jump_sound else None
                        else:
                            play_jump()
                    except Exception as e:
                        print(f"Jump sound error: {e}")
                else:
                    # Reset game
                    bird.y = int(float(bird_y))
                    pipes.clear()
                    score = 0
                    game_over = False
                    velocity_y = 0

        # Always update and draw
        if not game_over:
            move()

        draw()
        pygame.display.update()
        clock.tick(60)
        
        # Mobile audio keep-alive: periodically wake audio context
        if IS_WEB and not audio_armed:
            audio_keep_alive_counter += 1
            if audio_keep_alive_counter > 120:  # Every 2 seconds at 60fps
                audio_keep_alive_counter = 0
                try:
                    wake_audio_context()
                except:
                    pass

        await asyncio.sleep(0)


# Run the game
asyncio.run(main())

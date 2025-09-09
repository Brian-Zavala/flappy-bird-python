import pygame
import sys
import random
import asyncio
from pathlib import Path

# Fallback functions (defined first, may be overridden by import)
def init_audio_once():
    return False
def load_sounds():
    pass
def warmup_sounds():
    pass
def load_background_music():
    pass
def play_jump():
    pass
def play_crash():
    pass

# Try to import real sound functions
try:
    from sound_effects import (
        init_audio_once,
        load_sounds,
        warmup_sounds,
        load_background_music,
        play_jump,
        play_crash
    )
    print("Sound module loaded successfully")
except Exception as e:
    print(f"sound_effects import failed: {e} - using fallback functions")

# Game Variables
GAME_WIDTH = 360
GAME_HEIGHT = 640

# Check if running in web browser
IS_WEB = sys.platform == "emscripten"
ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

# bird class
bird_x = GAME_WIDTH / 8
bird_y = GAME_HEIGHT / 2
bird_width = 34
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

    # Initialize pygame (but NOT mixer yet - wait for user gesture)
    pygame.init()
    print(f"PYGAME INIT OK, IS_WEB = {IS_WEB}")

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

    # Load images AFTER set_mode
    def load_image_safe(path, use_alpha=True):
        try:
            img = pygame.image.load(str(path))
            if use_alpha:
                return img.convert_alpha()
            else:
                return img.convert()
        except Exception as e:
            print(f"Failed to load {path}: {e}")
            surf = pygame.Surface((64, 64))
            if "bird" in str(path):
                surf.fill((255, 255, 0))
            elif "pipe" in str(path):
                surf.fill((0, 255, 0))
            elif "bg" in str(path):
                surf.fill((135, 206, 235))
            else:
                surf.fill((255, 0, 255))
            return surf

    # Load all images
    background_image = load_image_safe(ASSETS / "flappybirdbg.png", False)
    background_image = pygame.transform.scale(background_image, (GAME_WIDTH, GAME_HEIGHT))

    bird_image = load_image_safe(ASSETS / "flappybird.png", True)
    bird_image = pygame.transform.scale(bird_image, (bird_width, bird_height))

    top_pipe_image = load_image_safe(ASSETS / "toppipe.png", True)
    top_pipe_image = pygame.transform.scale(top_pipe_image, (pipe_width, pipe_height))

    bottom_pipe_image = load_image_safe(ASSETS / "bottompipe.png", True)
    bottom_pipe_image = pygame.transform.scale(bottom_pipe_image, (pipe_width, pipe_height))

    emoji_image = load_image_safe(ASSETS / "score.png", True)
    emoji_image = pygame.transform.scale(emoji_image, (75, 75))

    # Game state
    bird = Bird(bird_image)
    pipes = []
    velocity_x = -2
    velocity_y = 0
    gravity = 0.4
    score = 0
    game_over = False
    
    # Audio state - wait for first user gesture
    audio_initialized = False
    
    def init_audio_on_first_gesture():
        """Initialize audio on first user interaction (tap/click/keydown)."""
        nonlocal audio_initialized
        if audio_initialized:
            return

        # Mark immediately to prevent repeated calls
        audio_initialized = True

        try:
            # Initialize mixer if not already
            init_audio_once()

            # Always load + warm + music (don't skip if mixer already running)
            load_sounds()
            warmup_sounds()
            load_background_music()

            print("✓ Audio system initialized on first gesture")
        except Exception as e:
            print(f"Audio init failed: {e}")

    def draw():
        window.blit(background_image, (0, 0))

        # Draw bird
        window.blit(bird.img, bird)

        # Draw pipes
        for pipe in pipes:
            window.blit(pipe.img, pipe)

        # Score display (original styling)
        emoji_rect = emoji_image.get_rect(topleft=(5, 6))
        window.blit(emoji_image, emoji_rect)

        score_str = str(int(score))
        text_surf = font_small.render(score_str, True, (255, 255, 255))

        pad = 16
        inner = emoji_rect.inflate(-2 * pad, -2 * pad)
        text_rect = text_surf.get_rect(center=inner.center)
        window.blit(text_surf, text_rect)

        # Draw game over text (properly centered)
        if game_over:
            game_over_txt = font.render("GAME OVER", True, (255, 255, 255))
            game_over_x = GAME_WIDTH / 2 - game_over_txt.get_width() / 2
            game_over_y = GAME_HEIGHT / 2 - 50
            window.blit(game_over_txt, (game_over_x, game_over_y))
            
            restart_txt = font_small.render("Tap to restart", True, (255, 255, 255))
            restart_x = GAME_WIDTH / 2 - restart_txt.get_width() / 2
            restart_y = GAME_HEIGHT / 2
            window.blit(restart_txt, (restart_x, restart_y))

    def create_pipe():
        gap = 180
        pipe_y_min = gap
        pipe_y_max = GAME_HEIGHT - gap
        pipe_y = random.randint(pipe_y_min, pipe_y_max)

        top_pipe = Pipe(top_pipe_image)
        top_pipe.x = pipe_x
        top_pipe.y = pipe_y - pipe_height - (gap / 2)

        bottom_pipe = Pipe(bottom_pipe_image)
        bottom_pipe.x = pipe_x
        bottom_pipe.y = pipe_y + (gap / 2)

        pipes.extend([top_pipe, bottom_pipe])

    def move():
        global velocity_y, score, game_over
        
        velocity_y += gravity
        bird.y += int(float(velocity_y))
        bird.y = max(bird.y, 0)

        if bird.y > GAME_HEIGHT:
            game_over = True
            if audio_initialized:
                try:
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
                if audio_initialized:
                    try:
                        play_crash()
                    except Exception as e:
                        print(f"Crash sound error: {e}")

        while len(pipes) > 0 and pipes[0].x + pipe_width < -pipe_width:
            pipes.pop(0)

    # Timer for pipe creation
    create_pipes_timer = pygame.USEREVENT + 1
    pygame.time.set_timer(create_pipes_timer, 1500)

    # Main game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop() if audio_initialized else None
                pygame.quit()
                return

            if event.type == create_pipes_timer and not game_over:
                create_pipe()

            # Handle keyboard input
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_x, pygame.K_UP):
                    # Initialize audio on first interaction
                    init_audio_on_first_gesture()
                    
                    if not game_over:
                        velocity_y = -6
                        if audio_initialized:
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

            # Handle touch/mouse input (including mobile FINGERDOWN)
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                # Initialize audio on first interaction
                init_audio_on_first_gesture()
                
                if not game_over:
                    velocity_y = -6
                    if audio_initialized:
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

        # Update and draw
        if not game_over:
            move()

        draw()
        pygame.display.update()
        clock.tick(60)

        await asyncio.sleep(0)


# Run the game
asyncio.run(main())
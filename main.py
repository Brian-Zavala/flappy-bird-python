import pygame
import sys
import random
import asyncio
from pathlib import Path
import theme_changer
from difficulty import difficulty_factor, current_gap, vertical_pipe_enabled

# ---- audio wiring (namespace import; no shadowing) ----
try:
    import sound_effects as sfx
    print("Sound module loaded successfully")
except Exception as e:
    print(f"sound_effects import failed: {e} - using no-op audio")
    class _NoAudio:
        def init_audio_once(self): return False
        def load_sounds(self): pass
        def warmup_sounds(self): pass
        def load_background_music(self): pass
        def play_jump(self): pass
        def play_crash(self): pass
        def play_score_sound(self): pass
        def play_fall(self): pass
        def play_swoosh(self): pass

    sfx = _NoAudio()

# Game Variables
GAME_WIDTH = 360
GAME_HEIGHT = 640

# bird pitch constants 
MAX_PITCH_UP_DEG    = 58.0    # nose-up clamp
MAX_PITCH_DOWN_DEG  = -90.0   # nose-down clamp
PITCH_GAIN          = 15.0     # maps velocity_y -> degrees
PITCH_LERP_PER_SEC  = 6.0    # smoothing speed (higher = snappier)




# Check if running in web browser
IS_WEB = sys.platform == "emscripten"
ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

# bird class
bird_x = GAME_WIDTH / 8
bird_y = GAME_HEIGHT / 2
bird_width = 44
bird_height = 34


# Pipe class
pipe_x = GAME_WIDTH
pipe_y = 0
pipe_width = 64
pipe_height = 512

# simple dt timer
last_time = pygame.time.get_ticks()

next_pair_id = 0  # unique id for each pipe pair

class Bird(pygame.Rect):
    def __init__(self, img_middle_flap):
        pygame.Rect.__init__(self, bird_x, bird_y, bird_width, bird_height)
        # animation frames and state
        self.frames = []
        self.frame_index = 1
        self.img = img_middle_flap
        self.pitch = 0.0  # degrees, +up / -down

        # simple aimation timer
        self.frame_ms = 90
        self._accum_ms = 0

        # when player flaps, show "up" frame for a bit
        self.flap_lock_ms = 120
        self._flap_timer = 0

    def set_frames(self, up, mid, down):
        self.frames = [down, mid, up]
        self.frame_index = 1
        self.img = self.frames[self.frame_index]

    def on_flap(self):
        # Call rught after velocity_y is set (velocity_y = -6)
        self._flap_timer = self.flap_lock_ms
        self.frame_index = 2  # show "up" frame immediately
        self.img =self.frames[self.frame_index]

    def update(self, dt_ms: int, velocity_y: float):
        """Advance animation. dt_ms is milliseconds since last frame."""
        # Countdown flap lock if active
        if self._flap_timer > 0:
            self._flap_timer -= dt_ms
            # keep showing "up" frame while locked
            self.frame_index = 2
            self.img = self.frames[self.frame_index]
            return

        # Otherwise, run a simple 3-frame cycle (down -> mid -> up -> mid -> ...)
        self._accum_ms += dt_ms
        if self._accum_ms >= self.frame_ms:
            self._accum_ms = 0
            # pattern: 0,1,2,1,0,1,2,1,...
            if self.frame_index == 0:        # down -> mid
                self.frame_index = 1
            elif self.frame_index == 1:      # mid -> up
                self.frame_index = 2
            else:                             # up -> mid
                self.frame_index = 1
            self.img = self.frames[self.frame_index]

        # (Optional) bias the frame by velocity for extra feedback:
        if velocity_y < -2: self.frame_index = 2  # going up
        elif velocity_y > 3: self.frame_index = 0 # falling
        self.img = self.frames[self.frame_index]

class Pipe(pygame.Rect):
    def __init__(self, img):        
        pygame.Rect.__init__(self, pipe_x, pipe_y, pipe_width, pipe_height)
        self.img = img
        self.passed = False
        self.vy = 0.0
        self.pair_gap = 0
        self.frozen = True
        self.frozen_y = 0


async def main():
    global bird, pipes, velocity_x, velocity_y, gravity, score, game_over, window, clock

    

    # Initialize pygame but immediately quit mixer to control it later
    pygame.init()

    # Immediately quit mixer so we can initialize it properly on first gesture
    if pygame.mixer.get_init():
        pygame.mixer.quit()
        print("Quit auto-initialized mixer to control initialization timing")
    print(f"PYGAME INIT OK (mixer disabled), IS_WEB = {IS_WEB}")

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
    background_image_day = load_image_safe(ASSETS / "flappybird_bg_day.png", False).convert()
    background_image_day = pygame.transform.scale(background_image_day, (GAME_WIDTH, GAME_HEIGHT))
    
    background_image_night = load_image_safe(ASSETS / "flappybird_bg_night.png", False).convert()
    background_image_night = pygame.transform.scale(background_image_night, (GAME_WIDTH, GAME_HEIGHT))

    base_image = load_image_safe(ASSETS / "base.png", True)
    base_image = pygame.transform.scale(base_image, (GAME_WIDTH, pipe_height // 8))
    base_rect = base_image.get_rect(topleft=(0, GAME_HEIGHT - base_image.get_height()))

    bird_up_image = load_image_safe(ASSETS / "redbird-upflap.png", True)
    bird_up_image = pygame.transform.scale(bird_up_image, (bird_width, bird_height))

    bird_mid_image= load_image_safe(ASSETS / "redbird-midflap.png", True)
    bird_mid_image = pygame.transform.scale(bird_mid_image, (bird_width, bird_height))

    bird_down_image = load_image_safe(ASSETS / "redbird-downflap.png", True)
    bird_down_image = pygame.transform.scale(bird_down_image, (bird_width, bird_height))

    top_pipe_image = load_image_safe(ASSETS / "toppipe.png", True)
    top_pipe_image = pygame.transform.scale(top_pipe_image, (pipe_width, pipe_height))

    bottom_pipe_image = load_image_safe(ASSETS / "bottompipe.png", True)
    bottom_pipe_image = pygame.transform.scale(bottom_pipe_image, (pipe_width, pipe_height))

    emoji_image = load_image_safe(ASSETS / "score.png", True)
    emoji_image = pygame.transform.scale(emoji_image, (75, 75))

    gameover_image = load_image_safe(ASSETS / "gameover.png", True)
    gameover_image = pygame.transform.scale(gameover_image, (192, 42))

    # Game state
    bird = Bird(bird_mid_image)
    bird.set_frames(bird_down_image, bird_mid_image, bird_up_image)
    pipes = []
    velocity_x = -2
    velocity_y = 0
    gravity = 0.4
    score = 0
    game_over = False

    # make sure bird has a pitch field
    if not hasattr(bird, "pitch"):
        bird.pitch = 0.0
    
    # Audio state - wait for first user gesture
    audio_initialized = False
    audio_failed_once = False  # allow retry if the first attempt fails
    
    def init_audio_on_first_gesture():
        """Initialize audio on first user interaction (tap/click/keydown)."""
        nonlocal audio_initialized, audio_failed_once
        if audio_initialized:
            return

        try:
            # Always coerce mixer into our known-good config inside the gesture
            sfx.ensure_mixer_config()
            sfx.load_sounds()
            sfx.warmup_sounds()
            sfx.load_background_music()
            audio_initialized = True
            print("✓ Audio unlocked & warmed")
        except Exception as e:
            audio_failed_once = True
            print(f"Audio init failed (will allow retry): {e}")
            # leave audio_initialized = False so the next tap retries
    
    # Optional: catch the earliest possible user gesture (helps if a loader overlay eats events)
    if IS_WEB:
        try:
            # These imports only exist in web environment (pyodide/emscripten)
            # We import here because they would fail on desktop Python
            import platform
            from pyodide.ffi import create_proxy
            def _unlock_from_js(_=None):
                init_audio_on_first_gesture()
            _proxy = create_proxy(_unlock_from_js)
            platform.window.addEventListener("pointerdown", _proxy, {"once": True, "capture": True})
            print("Global pointerdown capture set for audio unlock")
        except ImportError as e:
            print(f"Web-specific imports not available: {e}")
        except Exception as e:
            print(f"Global pointerdown capture not set: {e}")
    # Initialize theme state (removed transition check - will be in game loop)

    def draw():
        now = pygame.time.get_ticks()
        theme_state = theme_changer.get_theme_state()
        
        if not theme_state['transitioning']:
            if theme_state['current_theme'] == "day":
                window.blit(background_image_day, (0, 0))
            else:
                window.blit(background_image_night, (0, 0))
        else:
            # Crossfade
            t = (now - theme_state['transition_start']) / theme_changer.TRANSITION_MS
            if   t < 0: t = 0.0
            elif t > 1: t = 1.0
            alpha_to = int(t * 255)
            alpha_from = 255 - alpha_to

            # Copy so we can set per-surface alpha without mutating originals
            bg_from = background_image_day   if theme_state['transition_from'] == "day"   else background_image_night
            bg_to   = background_image_night if theme_state['transition_to']   == "night" else background_image_day

            a = bg_from.copy(); a.set_alpha(alpha_from); window.blit(a, (0, 0))
            b = bg_to.copy();   b.set_alpha(alpha_to);   window.blit(b, (0, 0))
    

        # Draw pipes
        for pipe in pipes:
            window.blit(pipe.img, pipe)

        # Draw base, after pipes so base sits on top of pipes
        window.blit(base_image, (0, GAME_HEIGHT - base_image.get_height()))

        # Draw bird (rotated by pitch)
        rot = pygame.transform.rotozoom(bird.img, bird.pitch, 1.0)
        rot_rect = rot.get_rect(center=bird.center)
        window.blit(rot, rot_rect)
        
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
            # Optional: draw game over text
            # game_over_txt = font.render("GAME OVER", True, (255, 255, 255))
            game_over_x = GAME_WIDTH / 2 - gameover_image.get_width() / 2
            game_over_y = GAME_HEIGHT / 2 - 50
            window.blit(gameover_image, (game_over_x, game_over_y))
            
            restart_txt = font_small.render("Tap to restart", True, (255, 255, 255))
            restart_x = GAME_WIDTH / 2 - restart_txt.get_width() / 2
            restart_y = GAME_HEIGHT / 2
            window.blit(restart_txt, (restart_x, restart_y))

    def create_pipe():
        gap = current_gap(score)

        # choose a vertical center safely on screen
        center_min = 120
        center_max = GAME_HEIGHT - base_rect.height - 120
        center_y = random.randint(center_min, center_max)

        # difficulty-scaled speed for THIS PAIR (top drives)
        factor = difficulty_factor(score)
        max_speed = 0.5 + factor * 1.5  # 0.5 → 2.0

        # top pipe (driver)
        top_pipe = Pipe(top_pipe_image)
        top_pipe.x = pipe_x
        top_pipe.y = center_y - gap // 2 - pipe_height
        top_pipe.vy = 0.0
        top_pipe.pair_gap = gap
        top_pipe.frozen = True
        top_pipe.frozen_y = top_pipe.y

        #  bottom pipe (follower) 
        bottom_pipe = Pipe(bottom_pipe_image)
        bottom_pipe.x = pipe_x
        bottom_pipe.y = center_y + gap // 2
        bottom_pipe.vy = 0.0
        bottom_pipe.pair_gap = gap
        bottom_pipe.frozen = True
        bottom_pipe.frozen_y = bottom_pipe.y

        #  append in order (top, bottom)
        pipes.extend([top_pipe, bottom_pipe])


    def move():
        global velocity_y, score, game_over

        # --- Bird physics ---
        velocity_y += gravity
        bird.y += int(float(velocity_y))
        bird.y = max(bird.y, 0)

        if bird.bottom > base_rect.top:
            bird.bottom = base_rect.top
            velocity_y = 0
            game_over = True
            try: sfx.play_fall()
            except Exception: pass
    
        # --- difficulty knobs ---
        factor = difficulty_factor(score)
        max_speed = 0.5 + factor * 1.5
        flip_chance = factor * 0.05

        enable_vertical = vertical_pipe_enabled(score)

        i = 0
        while i + 1 < len(pipes):
            top = pipes[i]
            bottom = pipes[i + 1]

            # horizontal scroll
            top.x += velocity_x
            bottom.x = top.x

            pair_gap = top.pair_gap if hasattr(top, "pair_gap") else current_gap(score)

            # bounds for moving state
            min_top_y = -pipe_height
            max_top_y = (GAME_HEIGHT - base_rect.height) - (pipe_height + pair_gap)

            if enable_vertical:
                # unfreeze on first frame of enabled state
                if top.frozen:
                    top.frozen = False
                    bottom.frozen = False
                    # seed vy once when coming out of freeze
                    top.vy = random.choice([-1, 1]) * random.uniform(0.3, max_speed)

                # vertical move
                top.y += top.vy

                # bounce within band
                if top.y < min_top_y:
                    top.y = min_top_y
                    top.vy *= -1
                elif top.y > max_top_y:
                    top.y = max_top_y
                    top.vy *= -1

                # occasional chaos flips ONLY when enabled
                if flip_chance > 0 and random.random() < flip_chance:
                    top.vy = random.choice([-1, 1]) * random.uniform(0.3, max_speed)

                # follower keeps exact stored gap
                bottom.y = top.y + pipe_height + pair_gap
            else:
                # HARD PIN — no recomputation, no drift
                if not top.frozen:
                    # capture current resting place so disabling mid-cycle doesn't jump
                    top.frozen_y = top.y
                    bottom.frozen_y = bottom.y
                    top.frozen = bottom.frozen = True

                top.vy = 0.0
                top.y = top.frozen_y
                bottom.y = bottom.frozen_y

            # scoring
            if (not getattr(top, "passed", False)) and bird.x > top.x + top.width:
                score += 1.0
                try: sfx.play_score_sound()
                except Exception: pass
                top.passed = bottom.passed = True

            # collisions
            if bird.colliderect(top) or bird.colliderect(bottom):
                game_over = True
                try: sfx.play_crash()
                except Exception: pass

            i += 2

        # purge off-screen pairs **after** iterating
        while len(pipes) >= 2 and pipes[0].x + pipe_width < -pipe_width:
            del pipes[0:2]


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
                        bird.on_flap()
                        # instant nose-up bias
                        bird.pitch = max(bird.pitch, 0.0)
                        if audio_initialized:
                            try:
                                sfx.play_jump()
                            except Exception as e:
                                print(f"Jump sound error: {e}")
                    else:
                        # Reset game
                        bird.y = int(float(bird_y))
                        bird.pitch = 0.0  # Reset bird pitch
                        pipes.clear()
                        score = 0
                        game_over = False
                        velocity_y = 0
                        # Reset theme to day on game restart
                        theme_changer.reset_theme()

            # Optional extra swoosh sounds on keyup            
            # if event.type == pygame.KEYUP:
            #     if event.key in (pygame.K_SPACE, pygame.K_x, pygame.K_UP):
            #         if not game_over:
            #             try:
            #                 sfx.play_swoosh()
            #             except Exception as e:
            #                 print(f"Swoosh sound error: {e}")

            # Handle touch/mouse input (including mobile FINGERDOWN)
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                # Initialize audio on first interaction
                init_audio_on_first_gesture()
                
                if not game_over:
                    velocity_y = -6
                    if audio_initialized:
                        try:
                            sfx.play_jump()
                        except Exception as e:
                            print(f"Jump sound error: {e}")
                else:
                    # Reset game
                    bird.y = int(float(bird_y))
                    bird.pitch = 0.0  # Reset bird pitch
                    pipes.clear()
                    score = 0
                    game_over = False
                    velocity_y = 0
                    # Reset theme to day on game restart
                    theme_changer.reset_theme()

        # Update and draw
        if not game_over:
            global last_time
            move()
            # ----- update bird pitch after velocity_y has changed in move() -----
            now = pygame.time.get_ticks()
            dt = (now - last_time) / 1000.0
            last_time = now

            # velocity -> target angle
            if game_over:
                target_pitch = MAX_PITCH_DOWN_DEG
            else:
                raw = -velocity_y * PITCH_GAIN  # negative vel (up) -> positive angle
                target_pitch = max(MAX_PITCH_DOWN_DEG, min(MAX_PITCH_UP_DEG, raw))

            # smooth toward target (fps independent)
            blend = min(1.0, PITCH_LERP_PER_SEC * dt)
            bird.pitch += (target_pitch - bird.pitch) * blend
            # ---------------------------------------------
            
            bird.update(int(dt * 1000), velocity_y)

            # Check if we should start a new transition based on current score
            theme_changer.maybe_start_theme_transition(now, score)
            
            # Check if current transition should complete
            theme_state = theme_changer.get_theme_state()
            if theme_state['transitioning'] and now - theme_state['transition_start'] >= theme_changer.TRANSITION_MS:
                theme_changer.complete_transition()

        draw()
        pygame.display.update()
        clock.tick(60)

        await asyncio.sleep(0)


# Run the game
asyncio.run(main())
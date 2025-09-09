import pygame
from pathlib import Path

# Absolute paths (safe in pygbag)
ROOT = Path(__file__).parent
SOUNDS = ROOT / "sounds"

# Module-level handles
jump_sound = None
crash_sound = None
music_loaded = False


def init_audio_once():
    """Init mixer exactly once with pygbag-recommended settings.
    Call this AFTER first user gesture, not on import."""
    if not pygame.mixer.get_init():
        # Pygbag recommended: OGG 16-bit 24kHz mono
        pygame.mixer.pre_init(frequency=24000, size=-16, channels=1, buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(8)  # SDL_mixer default
        print(f"Mixer initialized: {pygame.mixer.get_init()}")
        return True
    return False


def load_sounds():
    """Load all sound effects. Call after init_audio_once()."""
    global jump_sound, crash_sound
    
    try:
        # All audio should be OGG 24kHz mono for pygbag
        jump_sound = pygame.mixer.Sound(str(SOUNDS / "wing_flap.ogg"))
        print(f"✓ Jump sound loaded: {jump_sound.get_length():.2f}s")
    except Exception as e:
        print(f"Failed to load jump sound: {e}")
        jump_sound = None
    
    try:
        crash_sound = pygame.mixer.Sound(str(SOUNDS / "game_over.ogg"))
        print(f"✓ Crash sound loaded: {crash_sound.get_length():.2f}s")
    except Exception as e:
        print(f"Failed to load crash sound: {e}")
        crash_sound = None


def warmup_sounds():
    """Warm up sounds by playing them silently.
    Do this inside the first user gesture to ensure decoding."""
    for sound in (jump_sound, crash_sound):
        if sound:
            ch = pygame.mixer.find_channel(True)
            if ch:
                ch.play(sound)
                ch.stop()
    print("Sounds warmed up")


def load_background_music():
    """Load and start background music."""
    global music_loaded
    if music_loaded:
        return
    
    try:
        pygame.mixer.music.load(str(SOUNDS / "flappy_background_song.ogg"))
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)
        music_loaded = True
        print("✓ Background music started")
    except Exception as e:
        print(f"Failed to load background music: {e}")


def play_jump():
    """Play jump sound effect."""
    if jump_sound:
        jump_sound.play()


def play_crash():
    """Play crash sound effect."""
    if crash_sound:
        crash_sound.play()
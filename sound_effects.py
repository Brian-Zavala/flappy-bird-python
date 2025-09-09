import pygame
from pathlib import Path

# Absolute paths (safe in pygbag)
ROOT = Path(__file__).parent
SOUNDS = ROOT / "sounds"

# Module-level handles
jump_sound = None
crash_sound = None
SFX_CH = None  # dedicated SFX channel
SFX_READY = False


def init_audio_once(sample_rate=24000, channels=1, buffer=512):
    """Init mixer exactly once with mobile-friendly params.
    24kHz mono is recommended by pygbag docs for mobile compatibility."""
    if not pygame.mixer.get_init():
        # Use 24kHz mono as recommended by pygbag documentation
        pygame.mixer.pre_init(
            frequency=sample_rate, size=-16, channels=channels, buffer=buffer
        )
        pygame.mixer.init()
        # Fewer channels for better mobile performance
        pygame.mixer.set_num_channels(8)

    global SFX_CH
    if SFX_CH is None:
        # Simple channel allocation
        SFX_CH = pygame.mixer.Channel(0)
        SFX_CH.set_volume(1.0)


def init_sounds():
    """Load SFX. Call this after init_audio_once()."""
    global jump_sound, crash_sound
    
    # Try OGG first (pygbag recommended), fall back to WAV
    jump_paths = [
        SOUNDS / "wing_flap.ogg",
        SOUNDS / "wing_flap.wav"
    ]
    for path in jump_paths:
        try:
            if path.exists():
                jump_sound = pygame.mixer.Sound(str(path))
                print(f"✓ Loaded jump SFX: {path.name}")
                break
        except Exception as e:
            print(f"Could not load {path.name}:", e)
    else:
        print("⚠ No jump SFX loaded")
        jump_sound = None

    crash_paths = [
        SOUNDS / "game_over.ogg",
        SOUNDS / "game_over.wav"
    ]
    for path in crash_paths:
        try:
            if path.exists():
                crash_sound = pygame.mixer.Sound(str(path))
                print(f"✓ Loaded crash SFX: {path.name}")
                break
        except Exception as e:
            print(f"Could not load {path.name}:", e)
    else:
        print("⚠ No crash SFX loaded")
        crash_sound = None


def warmup_sfx():
    """Decode once so playback is instant on mobile."""
    global SFX_READY
    if SFX_READY:
        return

    for snd in (jump_sound, crash_sound):
        if snd:
            v = snd.get_volume()
            snd.set_volume(0.0)
            ch = pygame.mixer.find_channel(True)  # True = force a free one
            if ch:
                ch.play(snd)
                ch.stop()
            snd.set_volume(v)
    SFX_READY = True


def play_background():
    # Music as OGG is fine; keep volume modest so SFX cut through
    try:
        pygame.mixer.music.load(str(SOUNDS / "flappy_background_song.ogg"))
        pygame.mixer.music.set_volume(0.2)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print("Could not load/play background music:", e)


def _play_on_free_channel(snd):
    """Find a free channel and play sound."""
    if not snd:
        return
    # For mobile: use specific channel allocation
    try:
        # Try to use reserved channel first (more reliable on mobile)
        if SFX_CH and not SFX_CH.get_busy():
            SFX_CH.play(snd)
        else:
            # Fall back to finding any free channel
            ch = pygame.mixer.find_channel(False)  # False = don't force
            if ch:
                ch.play(snd)
            else:
                # Force a channel if none free
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.play(snd)
    except Exception as e:
        print(f"SFX play error: {e}")


def play_jump():
    if jump_sound:
        _play_on_free_channel(jump_sound)
    else:
        print("Jump sound not loaded")


def play_crash():
    if crash_sound:
        _play_on_free_channel(crash_sound)
    else:
        print("Crash sound not loaded")


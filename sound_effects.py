from pathlib import Path
import sys, pygame

IS_WEB = sys.platform == "emscripten"
ROOT = Path(__file__).parent
CANDIDATES = [ROOT/"assets"/"sounds", ROOT/"sounds"]
for base in CANDIDATES:
    if base.exists():
        SOUNDS = base; break
else:
    SOUNDS = ROOT

jump_sound = None
crash_sound = None
_music_loaded = False

def init_audio_once():
    """Init mixer with pygbag-friendly params, forcing correct settings."""
    # Always init with correct settings for web compatibility
    # Even if mixer was already initialized with wrong settings
    try:
        pygame.mixer.pre_init(frequency=24000, size=-16, channels=1, buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(8)
        print("Mixer initialized with web-friendly settings")
        return True
    except pygame.error as e:
        print(f"Mixer init error (may already be initialized): {e}")
        # Even if init fails, ensure we have the right number of channels
        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(8)
        return False

def _load(name: str):
    p = SOUNDS / name
    s = pygame.mixer.Sound(str(p))
    s.set_volume(0.6)
    return s

def load_sounds():
    global jump_sound, crash_sound
    # Prioritize OGG; they must be 24 kHz mono
    jump_sound  = _load("wing_flap.ogg")
    crash_sound = _load("game_over.ogg")  # Using game_over.ogg as your crash sound

def warmup_sounds():
    """Decode/cache inside the user gesture window."""
    for s in (jump_sound, crash_sound):
        if not s: continue
        vol = s.get_volume()
        s.set_volume(0.0)
        ch = pygame.mixer.find_channel(True)
        ch.play(s)
        ch.stop()
        s.set_volume(vol)

def load_background_music():
    global _music_loaded
    if _music_loaded: return
    try:
        pygame.mixer.music.load(str(SOUNDS / "flappy_background_song.ogg"))
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
        _music_loaded = True
    except Exception as e:
        print("bgm load failed:", e)

def play_jump():
    if jump_sound:
        jump_sound.play()

def play_crash():
    if crash_sound:
        crash_sound.play()
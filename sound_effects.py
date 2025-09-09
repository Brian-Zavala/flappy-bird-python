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

# Our expected, web-safe mixer configuration
_MIX_FREQ, _MIX_SIZE, _MIX_CHANS, _MIX_BUF = 24000, -16, 1, 512
_EXPECTED = (_MIX_FREQ, _MIX_SIZE, _MIX_CHANS)

def ensure_mixer_config():
    """Force mixer into the exact web-friendly config (idempotent, safe on mobile)."""
    init = pygame.mixer.get_init()  # None or (freq, size, channels)
    if init != _EXPECTED:
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        pygame.mixer.pre_init(_MIX_FREQ, _MIX_SIZE, _MIX_CHANS, _MIX_BUF)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(8)
        print("Mixer (re)initialized:", pygame.mixer.get_init())

def init_audio_once():
    """Kept for compatibility; called inside a gesture."""
    ensure_mixer_config()
    return True

def _load(name: str):
    p = SOUNDS / name
    s = pygame.mixer.Sound(str(p))
    s.set_volume(0.4)
    return s

def load_sounds():
    global jump_sound, crash_sound
    # Must use OGG Format! they must be 24 kHz mono!!
    jump_sound  = _load("wing_flap.ogg")
    crash_sound = _load("game_over.ogg")  

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
        pygame.mixer.music.set_volume(0.20)
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
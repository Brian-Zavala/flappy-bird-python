# Theme transition variables
TRANSITION_MS = 800
POINTS_PER_PHASE = 25

current_theme = "day"
transitioning = False
transition_from = "day"
transition_to = "day"
transition_start = 0
def desired_theme_for_score(score: float, POINTS_PER_PHASE: int) -> str:
    # Toggle every N points: 0–24 day, 25–49 night, 50–74 day, etc.
    phase = int(score) // POINTS_PER_PHASE
    theme = "night" if (phase % 2) else "day"
    return theme

def maybe_start_theme_transition(now_ms: int, score):
    global current_theme, transitioning, transition_from, transition_to, transition_start
    target = desired_theme_for_score(score, POINTS_PER_PHASE)
    if target != current_theme and not transitioning:
        transitioning = True
        transition_from = current_theme
        transition_to = target
        transition_start = now_ms

def complete_transition():
    """Complete the current transition and update the theme."""
    global current_theme, transitioning, transition_to
    if transitioning:
        old_theme = current_theme
        current_theme = transition_to
        transitioning = False

def reset_theme():
    """Reset theme to initial state (day)."""
    global current_theme, transitioning
    current_theme = "day"
    transitioning = False

def get_theme_state():
    """Get current theme state for rendering."""
    return {
        'current_theme': current_theme,
        'transitioning': transitioning,
        'transition_from': transition_from,
        'transition_to': transition_to,
        'transition_start': transition_start
    }

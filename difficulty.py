def difficulty_factor(score):
  """
  Returns a number between 0.0 and 1.0 that scales with score.
  - At score=0 → 0.0 (easy)
  - At score=30 → 1.0 (max chaos)
  """
  return min(1.0, score / 30.0)

def current_gap(score: float) -> int:
    base_gap = 180
    factor = difficulty_factor(score)  # 0 → 1
    return int(base_gap - factor * 60)  # 180 → 120

# after updating score, compute whether pipes should move this cycle
def vertical_pipe_enabled(score: float) -> bool:
    if score <= 10:
        return False  # keep still until player reaches 10 points
    cycle = int(score - 6) // 10   # 0,1,2,3...
    return (cycle % 2 == 0)        # even → move, odd → stop



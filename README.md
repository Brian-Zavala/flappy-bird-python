# Flappy Bird Python

A modern take on the classic Flappy Bird game built with Python and Pygame with a family joke thrown in (I had to make the kids laugh). Features smooth gameplay(60 fps), dynamic themes(day & dark), and web deployment support.

## Features

- **Dynamic Themes** - Day/night backgrounds that transition every 25 points with smooth crossfades
- **Realistic Physics** - Bird rotation based on velocity with smooth animations
- **Rich Audio** - Multiple sound effects including wing flaps, crashes, and point collection
- **Web Ready** - Optimized for browser deployment using pygbag
- **Mobile Friendly** - Touch controls and gesture-based audio initialization

## Controls

- **Space/X/Up Arrow** - Make the bird flap
- **Mouse/Touch** - Tap to flap (mobile support)
- **Any key after game over** - Restart

## Quick Start

```bash
# Install dependencies
pip install pygame-ce

# Run locally
python main.py

# Web deployment (optional)
pip install pygbag
python -m pygbag main.py
```

## Technical Highlights

- Async/await game loop for smooth web performance
- 24kHz mono audio optimization for cross-platform compatibility
- Delta-time based animations for consistent framerates
- Modular theme system with crossfade transitions
- Proper collision detection with ground and pipe systems

Built with **Pygame Community Edition** for enhanced web compatibility and modern Python support.

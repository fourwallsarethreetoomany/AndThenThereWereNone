# setup.py - Global display, tactical grid dimensions, and core math helpers
import pygame

WIDTH  = 1280
HEIGHT = 800

# 150px Heavy Scale Tactical Cells
CELL_SIZE = 150
GRID_COLS = (WIDTH // CELL_SIZE) + 1  # 9 tactical columns
GRID_ROWS = (HEIGHT // CELL_SIZE) + 1  # 6 tactical rows

# Core Theme Colors (Dark Crimson, Obsidian, and Blood Rust)
COLOR_BG_OBSIDIAN    = (12, 10, 12)
COLOR_PANEL_CRIMSON  = (28, 11, 15)
COLOR_PANEL_BORDER   = (84, 22, 31)
COLOR_CRIMSON_BRIGHT = (185, 34, 48)
COLOR_CRIMSON_MUTED  = (125, 26, 36)
COLOR_TEXT_LIGHT     = (238, 230, 230)
COLOR_TEXT_GOLD      = (232, 190, 100)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

def clamp(val, min_val, max_val):
    """Clamps a numeric value between min_val and max_val."""
    return max(min_val, min(val, max_val))
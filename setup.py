HEIGHT = 800
WIDTH  = 1280
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
# 11/4/2026 finally made it actually run, imported heapq, added pathfinding, added testing squads, added ui, added a lot of placeholders for the grids (theyre just colors and stuff for now)
# 11/9/2026 going to add first mission and force selector
def clamp(val, min_val, max_val): # casemate and other weapons who have a limited field of fire such as bipod mg etc
    return max(min_val, min(val, max_val))
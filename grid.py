# grid.py
import heapq
import pygame
from setup import CELL_SIZE

class Cell:
    def __init__(self, gx, gy, terrain_type="open"):
        self.gx = gx
        self.gy = gy
        self.terrain_type = terrain_type
        self.move_weight = 1.0
        self.cover_val = 0.05
        self.color = (55, 68, 50)
        self.occupant = None
        self.concealment = 0.1
        self.spot_bonus = 1.0
        self.track_degrade = 0.0
        self.armor = 0
        self.setup_terrain(terrain_type)

    def setup_terrain(self, t_type):
        self.terrain_type = t_type
        if t_type == "grass":
            self.move_weight = 1.0
            self.cover_val = 0.05
            self.concealment = 0.1
            self.spot_bonus = 1.0
            self.track_degrade = 0.0
            self.armor = 0
            self.color = (46, 117, 89)
        elif t_type == "dry river":
            self.move_weight = 1.5
            self.cover_val = 0.05
            self.concealment = 0.05
            self.spot_bonus = 1.0
            self.track_degrade = 0.0
            self.armor = 0
            self.color = (111, 117, 126)
        elif t_type == "wall":
            self.move_weight = 1.5
            self.cover_val = 0.95
            self.concealment = 0.05
            self.spot_bonus = 1.0
            self.track_degrade = 0.0
            self.armor = 0
            self.color = (111, 117, 126)
        elif t_type == "fence river":
            self.move_weight = 1.5
            self.cover_val = 0.05
            self.concealment = 0.05
            self.spot_bonus = 1.0
            self.track_degrade = 0.0
            self.armor = 0
            self.color = (111, 117, 126)
        elif t_type == "road":
            self.move_weight = 0.4
            self.cover_val = 0.0
            self.color = (110, 110, 110)
        elif t_type == "open":
            self.move_weight = 1.0
            self.cover_val = 0.15
            self.color = (58, 126, 68)
        elif t_type == "rough":
            self.move_weight = 2.0
            self.cover_val = 0.45
            self.color = (111, 117, 126)
        elif t_type == "forest":
            self.move_weight = 2.6
            self.cover_val = 0.80
            self.color = (119, 163, 122)
        elif t_type == "building":
            self.move_weight = 999.0
            self.cover_val = 0.95
            self.color = (105, 100, 95)

class TacticalGrid:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[Cell(x, y) for y in range(rows)] for x in range(cols)]
        self.generate_procedural_map()

    def set_cell_terrain(self, gx, gy, t_type):
        cell = self.get_cell(gx, gy)
        if cell:
            cell.setup_terrain(t_type)

    def generate_procedural_map(self):
        # Road placed across the middle row safely
        road_y = min(7, self.rows // 2)
        for x in range(self.cols):
            self.set_cell_terrain(x, road_y, "road")

        # Forest patches
        for x in range(4, 9):
            for y in range(2, 6):
                self.set_cell_terrain(x, y, "forest")

        for x in range(22, 28):
            for y in range(9, 14):
                self.set_cell_terrain(x, y, "forest")

        # Rough terrain
        for x in range(12, 17):
            for y in range(10, 14):
                self.set_cell_terrain(x, y, "rough")

        # Walls & river beds
        for x in range(8, 12):
            self.set_cell_terrain(x, 3, "wall")

        for y in range(8, 14):
            self.set_cell_terrain(20, y, "dry river")

        # Buildings
        buildings = [(15, 3), (16, 3), (15, 4), (16, 4)]
        for bx, by in buildings:
            self.set_cell_terrain(bx, by, "building")

    def get_cell(self, gx, gy):
        if 0 <= gx < self.cols and 0 <= gy < self.rows:
            return self.cells[gx][gy]
        return None

    def world_to_grid(self, wx, wy):
        return int(wx // CELL_SIZE), int(wy // CELL_SIZE)

    def grid_to_world_center(self, gx, gy):
        return pygame.Vector2(gx * CELL_SIZE + CELL_SIZE / 2, gy * CELL_SIZE + CELL_SIZE / 2)

    def draw(self, surface):
        for x in range(self.cols):
            for y in range(self.rows):
                c = self.cells[x][y]
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(surface, c.color, rect)
                pygame.draw.rect(surface, (38, 48, 34), rect, 1)
                if c.cover_val >= 0.7:
                    pygame.draw.circle(surface, (20, 42, 18), rect.center, 5)

def astar_pathfind(grid: TacticalGrid, start_gx, start_gy, goal_gx, goal_gy, order_mode, moving_team):
    goal_cell = grid.get_cell(goal_gx, goal_gy)
    if not goal_cell or goal_cell.move_weight >= 999.0:
        return []
    if goal_cell.occupant is not None and goal_cell.occupant != moving_team:
        return []

    frontier = []
    heapq.heappush(frontier, (0, (start_gx, start_gy)))
    came_from = {(start_gx, start_gy): None}
    cost_so_far = {(start_gx, start_gy): 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        cx, cy = current

        if current == (goal_gx, goal_gy):
            break

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            neighbor = grid.get_cell(nx, ny)
            if not neighbor or neighbor.move_weight >= 999.0:
                continue
            if neighbor.occupant is not None and (nx, ny) != (goal_gx, goal_gy) and neighbor.occupant != moving_team:
                continue

            if order_mode in ["Normal", "Quick"]:
                step_cost = neighbor.move_weight
            elif order_mode == "Fast":
                step_cost = 0.2 if neighbor.terrain_type == "road" else (neighbor.move_weight * 1.5)
            elif order_mode == "Sneak":
                step_cost = (1.05 - neighbor.cover_val) * 8.0
            elif order_mode == "Assault":
                has_adj_cover = False
                for ax, ay in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    adj = grid.get_cell(nx + ax, ny + ay)
                    if adj and adj.cover_val >= 0.4:
                        has_adj_cover = True
                        break
                step_cost = 0.6 if has_adj_cover else (neighbor.move_weight * 1.8)
            else:
                step_cost = neighbor.move_weight

            new_cost = cost_so_far[current] + step_cost
            if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                cost_so_far[(nx, ny)] = new_cost
                h = abs(goal_gx - nx) + abs(goal_gy - ny)
                heapq.heappush(frontier, (new_cost + h, (nx, ny)))
                came_from[(nx, ny)] = current

    if (goal_gx, goal_gy) not in came_from:
        return []

    curr = (goal_gx, goal_gy)
    path = []
    while curr != (start_gx, start_gy):
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path
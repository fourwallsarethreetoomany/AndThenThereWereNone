# unit.py - Individual infantry simulation, squads, formations, and fireteam control
import math
import random
import pygame

try:
    from setup import CELL_SIZE
except ImportError:
    try:
        from setup import CELL_SIZE
    except ImportError:
        CELL_SIZE = 150

from combat import Projectile
from equipment import Gun
from grid import TacticalGrid, astar_pathfind

# Crimson & Obsidian Theme Colors for Combat Render
COLOR_BLUE_SOLDIER   = (55, 125, 220)
COLOR_RED_SOLDIER    = (215, 45, 55)
COLOR_SELECTED_RING  = (240, 205, 90)
COLOR_SUPPRESSED_TINT= (180, 80, 60)
COLOR_DEAD_SOLDIER   = (65, 55, 60)

class Soldier:
    def __init__(self, name, rank, weapon="weapon", gun_obj=None, grenades_obj=None, radio_obj=None):
        self.name = name
        self.rank = rank
        self.weapon = weapon
        self.condition = 200        # 200 = Peak condition, 100 = Incapacitated, 0 = KIA
        self.morale = 100           # 0 to 100
        self.is_pinned = False
        self.assigned_squad = None
        self.assigned_fireteam = None
        self.gun = gun_obj if gun_obj else Gun(weapon)
        self.grenades = grenades_obj
        self.radio = radio_obj
        self.pos = pygame.Vector2(0, 0)
        self.facing_angle = 0.0

    def calculate_cost(self):
        base_req = 10
        base_rar = 0
        if self.gun:
            base_req += self.gun.req_points
            base_rar += self.gun.rarity_points
        if self.grenades:
            base_req += self.grenades.req_points
            base_rar += self.grenades.rarity_points
        if self.radio:
            base_req += self.radio.req_points
            base_rar += self.radio.rarity_points
        return base_req, base_rar


class Squad:
    def __init__(self, squad_leader: Soldier):
        self.leader = squad_leader
        self.members = []
        self.formation_spread = 32  # Spacing in pixels adapted to 150px grid
        self.communication_link = True
        self.fireteams = []

    def add_member(self, soldier: Soldier):
        soldier.assigned_squad = self
        self.members.append(soldier)

    def update_morale(self):
        if self.leader.morale < 30 or self.leader.condition <= 0:
            for member in self.members:
                member.morale = max(0, member.morale - 4)

    def calculate_points(self):
        total_req = 0
        total_rar = 0
        for m in self.members:
            r, rar = m.calculate_cost()
            total_req += r
            total_rar += rar
        return total_req, total_rar


class InfantryTeam(pygame.sprite.Sprite):
    def __init__(self, name, squad, team_color="blue", gx=0, gy=0):
        super().__init__()
        self.name = name
        self.squad = squad
        self.team = team_color
        self.members = []
        self.gx = gx
        self.gy = gy
        self.pos = pygame.Vector2(gx * CELL_SIZE + CELL_SIZE // 2, gy * CELL_SIZE + CELL_SIZE // 2)
        self.path = []
        self.move_order = "Normal"
        self.speed = 1.6
        self.selected = False
        self.collision_radius = 28
        self.under_fire = False
        self.shoot_cooldown = random.randint(5, 20)
        self.suppression = 0.0
        self.current_action = "Observing"
        self.mounted = False
        self.assigned_vehicle = None
        self.formation_spread = 26

        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def add_soldier(self, soldier: Soldier):
        soldier.assigned_fireteam = self
        self.members.append(soldier)
        self.squad.add_member(soldier)
        self.update_soldier_positions()

    def get_soldier_world_pos(self, index):
        count = len(self.members)
        if count == 0:
            return pygame.Vector2(self.pos)
        
        # Staggered tactical wedge/column formation
        row = index // 2
        col = (index % 2) * 2 - 1
        ox = col * (self.formation_spread * 0.65)
        oy = (row - count / 4.0) * self.formation_spread
        return self.pos + pygame.Vector2(ox, oy)

    def update_soldier_positions(self):
        for idx, s in enumerate(self.members):
            s.pos = self.get_soldier_world_pos(idx)

    def total_health(self):
        return sum(m.condition for m in self.members)

    def avg_morale(self):
        if not self.members:
            return 0
        return sum(m.morale for m in self.members) / len(self.members)

    def calculate_points(self):
        r, rar = 0, 0
        for m in self.members:
            cr, crar = m.calculate_cost()
            r += cr
            rar += crar
        if self.assigned_vehicle:
            r += getattr(self.assigned_vehicle, "req_points", 0)
            rar += getattr(self.assigned_vehicle, "rarity_points", 0)
        return r, rar

    def apply_damage(self, caliber, projectile_type, soldier_index=None):
        damage = max(20, caliber * 0.45)
        self.suppression = min(100.0, self.suppression + 32.0)
        self.under_fire = True

        # Target specific soldier or first living member
        target_soldier = None
        if soldier_index is not None and 0 <= soldier_index < len(self.members):
            if self.members[soldier_index].condition > 0:
                target_soldier = self.members[soldier_index]

        if not target_soldier:
            for s in self.members:
                if s.condition > 0:
                    target_soldier = s
                    break

        if target_soldier:
            target_soldier.condition = max(0, target_soldier.condition - int(damage))
            target_soldier.morale = max(0, target_soldier.morale - 18)

    def set_order(self, order_name):
        self.move_order = order_name
        if order_name == "Normal":
            self.speed = 1.6
        elif order_name == "Quick":
            self.speed = 2.7
        elif order_name == "Fast":
            self.speed = 3.2
        elif order_name == "Sneak":
            self.speed = 0.95
        elif order_name == "Assault":
            self.speed = 2.1
        elif order_name == "Halt":
            self.path.clear()
        elif order_name == "Mount":
            self.mounted = True
            self.current_action = "Mounted"
        elif order_name == "Dismount":
            self.mounted = False
            self.current_action = "Dismounted"

    def update(self, grid: TacticalGrid, all_teams, projectiles_group):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if self.suppression > 0:
            self.suppression = max(0.0, self.suppression - 0.12)

        # Engagement scanning
        target_enemy = None
        closest_dist = 9999.0

        for other in all_teams:
            if other.team != self.team and other.total_health() > 0:
                dist = self.pos.distance_to(other.pos)
                if dist < 320 and dist < closest_dist:
                    closest_dist = dist
                    target_enemy = other

        if target_enemy:
            if self.move_order == "Sneak" and self.under_fire:
                self.current_action = "Evading"
                best_cover = None
                best_val = -1
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        c = grid.get_cell(self.gx + dx, self.gy + dy)
                        if c and getattr(c, "move_weight", 1.0) < 999.0 and getattr(c, "cover_val", 0) > best_val:
                            best_val = c.cover_val
                            best_cover = c
                if best_cover and (best_cover.gx, best_cover.gy) != (self.gx, self.gy):
                    self.path = astar_pathfind(grid, self.gx, self.gy, best_cover.gx, best_cover.gy, "Sneak", self)
                self.under_fire = False

            if self.move_order == "Assault" and closest_dist <= 160:
                self.path.clear()
                self.current_action = "Assault Firing"
                if self.shoot_cooldown <= 0:
                    for s in self.members:
                        if s.condition > 0 and random.random() < 0.65:
                            projectiles_group.add(Projectile(s.pos.x, s.pos.y, 1, target_enemy.pos, 0, 7.62, "ball", self.team))
                    self.shoot_cooldown = 35
            elif self.shoot_cooldown <= 0:
                self.current_action = "Engaging"
                for s in self.members:
                    if s.condition > 0 and random.random() < 0.4:
                        projectiles_group.add(Projectile(s.pos.x, s.pos.y, 1, target_enemy.pos, 0, 7.62, "ball", self.team))
                self.shoot_cooldown = 48
        elif self.path:
            self.current_action = f"Advancing ({self.move_order})"
        else:
            self.current_action = "Observing"

        # Movement path handling
        if self.path:
            nxt_gx, nxt_gy = self.path[0]
            target_pos = grid.grid_to_world_center(nxt_gx, nxt_gy)
            vec = target_pos - self.pos
            dist = vec.length()
            if dist <= self.speed:
                curr_cell = grid.get_cell(self.gx, self.gy)
                if curr_cell and getattr(curr_cell, "occupant", None) == self:
                    curr_cell.occupant = None

                self.pos = target_pos
                self.gx, self.gy = nxt_gx, nxt_gy
                self.path.pop(0)

                new_cell = grid.get_cell(self.gx, self.gy)
                if new_cell:
                    new_cell.occupant = self
            else:
                self.pos += vec.normalize() * self.speed

        self.update_soldier_positions()
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def draw(self, surface):
        if self.total_health() <= 0:
            return

        # Render movement trajectory line
        if self.selected and self.path:
            pts = [self.pos] + [pygame.Vector2(gx * CELL_SIZE + CELL_SIZE // 2, gy * CELL_SIZE + CELL_SIZE // 2) for gx, gy in self.path]
            if len(pts) > 1:
                pygame.draw.lines(surface, (230, 195, 75), False, pts, 2)

        # Draw individual soldiers
        for idx, s in enumerate(self.members):
            spos = self.get_soldier_world_pos(idx)
            sx, sy = int(spos.x), int(spos.y)

            if s.condition <= 0:
                # Casualty marker
                pygame.draw.line(surface, COLOR_DEAD_SOLDIER, (sx - 4, sy - 4), (sx + 4, sy + 4), 2)
                pygame.draw.line(surface, COLOR_DEAD_SOLDIER, (sx - 4, sy + 4), (sx + 4, sy - 4), 2)
                continue

            base_color = COLOR_BLUE_SOLDIER if self.team == "blue" else COLOR_RED_SOLDIER
            if self.suppression > 50:
                base_color = COLOR_SUPPRESSED_TINT

            # Body circle
            pygame.draw.circle(surface, base_color, (sx, sy), 5)
            # Helmet outline
            pygame.draw.circle(surface, (20, 18, 20), (sx, sy), 6, 1)

            # Selected indicator halo per soldier
            if self.selected:
                pygame.draw.circle(surface, COLOR_SELECTED_RING, (sx, sy), 9, 1)

        # Team leader chevron or squad bounding circle when selected
        if self.selected:
            pygame.draw.circle(surface, (220, 50, 60), (int(self.pos.x), int(self.pos.y)), self.collision_radius, 1)
# unit.py  define units and their behavior, remember to import units to main
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

from combat import Projectile, MuzzleFlash
from equipment import Gun
from grid import TacticalGrid, astar_pathfind

# black and red placeholder 
COLOR_BLUE_SOLDIER   = (55, 125, 220)
COLOR_RED_SOLDIER    = (215, 45, 55)
COLOR_SELECTED_RING  = (240, 205, 90)
COLOR_SUPPRESSED_TINT= (180, 80, 60)
COLOR_DEAD_SOLDIER   = (65, 55, 60) #placeholder, make a red cross symbol later

 
class CasualtyMarker(pygame.sprite.Sprite):
    def __init__(self, pos, team="blue", soldier_name="", soldier_rank=""):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.team = team
        self.soldier_name = soldier_name
        self.soldier_rank = soldier_rank
        self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def draw(self, surface, camera_offset=(0, 0)):
        cx = int(self.pos.x - camera_offset[0])
        cy = int(self.pos.y - camera_offset[1])
        pygame.draw.circle(surface, (34, 22, 26), (cx, cy), 6)
        cross_color = (185, 38, 48) if self.team == "red" else (115, 155, 210)
        pygame.draw.line(surface, cross_color, (cx - 4, cy), (cx + 4, cy), 2)
        pygame.draw.line(surface, cross_color, (cx, cy - 4), (cx, cy + 4), 2)
        pygame.draw.circle(surface, (15, 10, 12), (cx, cy), 6, 1)
 


class Soldier:
    def __init__(self, name, rank, weapon="weapon", gun_obj=None, grenades_obj=None, radio_obj=None, binoculars_obj=None):
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
        self.binoculars = binoculars_obj  
        self.pos = pygame.Vector2(0, 0)
        self.facing_angle = 0.0

    def calculate_cost(self):
        base_req = 1
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
        if self.binoculars:
            base_req += self.binoculars.req_points
            base_rar += self.binoculars.rarity_points
        return base_req, base_rar


class Squad:
    def __init__(self, squad_leader: Soldier):
        self.leader = squad_leader
        self.members = []
        self.formation_spread = 32  
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
    def __init__(self, name, squad, team_color="blue", gx=0, gy=0, casualties_group=None, effects_group=None):
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
 
        self.casualties_group = casualties_group
        self.effects_group = effects_group
        self.local_casualties = []
        self.initial_member_count = 0
        self.spotting_limit = 450.0
        self.experience = 1.0
        self.range_estimate_interval = 600
        self.spotted_targets = {}
 

        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def add_soldier(self, soldier: Soldier):
        soldier.assigned_fireteam = self
        self.members.append(soldier)
        self.initial_member_count += 1 
        self.squad.add_member(soldier)
        self.update_soldier_positions()
 
    def has_binoculars(self):
        return any(getattr(s, "binoculars", None) is not None for s in self.members if s.condition > 0)

    def get_binoculars_spot_bonus(self):
        bonuses = [s.binoculars.spot_bonus for s in self.members if s.condition > 0 and getattr(s, "binoculars", None) is not None]
        return max(bonuses) if bonuses else 1.0
 

    def get_soldier_world_pos(self, index):
        count = len(self.members)
        if count == 0:
            return pygame.Vector2(self.pos)
        
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
    def apply_damage(self, caliber, projectile_type, soldier_index=None, penetration=0):
        damage = max(20, caliber * 0.45)
        self.suppression = min(100.0, self.suppression + 32.0)
        self.under_fire = True

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
 
            if target_soldier.condition <= 0:
                death_pos = pygame.Vector2(target_soldier.pos)
                marker = CasualtyMarker(death_pos, self.team, target_soldier.name, target_soldier.rank)
                if self.casualties_group is not None:
                    self.casualties_group.add(marker)
                else:
                    self.local_casualties.append(marker)

                if target_soldier in self.members:
                    self.members.remove(target_soldier)
                if self.squad and target_soldier in self.squad.members:
                    self.squad.members.remove(target_soldier)

                self.update_soldier_positions() 
    def compute_range_estimate(self, enemy):
        real_range = self.pos.distance_to(enemy.pos)
        error_mult = 5.0 if self.has_binoculars() else 50.0
        error_pixels = error_mult * self.experience * (1 + (real_range / 1000.0))
        sign = random.choice([-1, 1])
        estimated_range = max(0.0, real_range + sign * error_pixels)

        direction = enemy.pos - self.pos
        if direction.length_squared() > 0:
            estimated_pos = self.pos + direction.normalize() * estimated_range
        else:
            estimated_pos = pygame.Vector2(self.pos)

        return real_range, estimated_range, estimated_pos

    def update_tacai_spotting(self, grid: TacticalGrid, all_units, force_estimate=False):
        obs_cell = grid.get_cell(self.gx, self.gy)
        spot_bonus = getattr(obs_cell, "spot_bonus", 1.0) if obs_cell else 1.0
        bino_bonus = self.get_binoculars_spot_bonus()

        active_enemies = set()
        for other in all_units:
            if other.team == self.team or other.total_health() <= 0:
                continue
            active_enemies.add(other)

            real_range = self.pos.distance_to(other.pos)
            tgt_cell = grid.get_cell(other.gx, other.gy)
            concealment = getattr(tgt_cell, "concealment", 0.0) if tgt_cell else 0.0
            effective_limit = self.spotting_limit * spot_bonus * bino_bonus * max(0.2, 1.0 - concealment)

            if real_range <= effective_limit:
                if other not in self.spotted_targets or force_estimate:
                    r_real, r_est, p_est = self.compute_range_estimate(other)
                    self.spotted_targets[other] = {
                        "real_range": r_real,
                        "estimated_range": r_est,
                        "estimated_pos": p_est,
                        "estimate_timer": self.range_estimate_interval,
                    }
                else:
                    entry = self.spotted_targets[other]
                    entry["real_range"] = real_range
                    entry["estimate_timer"] -= 1
                    if entry["estimate_timer"] <= 0:
                        r_real, r_est, p_est = self.compute_range_estimate(other)
                        entry["real_range"] = r_real
                        entry["estimated_range"] = r_est
                        entry["estimated_pos"] = p_est
                        entry["estimate_timer"] = self.range_estimate_interval
            else:
                self.spotted_targets.pop(other, None)

        for stale in [e for e in self.spotted_targets if e not in active_enemies]:
            self.spotted_targets.pop(stale, None)
 

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
 
    def _fire_at(self, aim_pos, projectiles_group, fire_prob=0.4):
        for s in self.members:
            if s.condition > 0 and random.random() < fire_prob:
                projectiles_group.add(Projectile(s.pos.x, s.pos.y, 1, aim_pos, 0, 7.62, "ball", self.team, penetration=8))
                if self.effects_group is not None:
                    self.effects_group.add(MuzzleFlash(s.pos, aim_pos - s.pos, size=7, duration=5))
 

    def update(self, grid: TacticalGrid, all_units, projectiles_group):
        if self.total_health() <= 0 and not self.assigned_vehicle:
            self.path.clear()
            self.spotted_targets.clear()
            curr_cell = grid.get_cell(self.gx, self.gy)
            if curr_cell and getattr(curr_cell, "occupant", None) == self:
                curr_cell.occupant = None
            self.kill()
            return

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if self.suppression > 0:
            self.suppression = max(0.0, self.suppression - 0.12)

        self.update_tacai_spotting(grid, all_units)

        target_enemy = None
        target_data = None
        closest_est_dist = 9999.0

        for enemy, data in self.spotted_targets.items():
            est_dist = data["estimated_range"]
            if est_dist < 320 and est_dist < closest_est_dist:
                closest_est_dist = est_dist
                target_enemy = enemy
                target_data = data

        if target_enemy and target_data:
            aim_pos = target_data["estimated_pos"]
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

            if self.move_order == "Assault" and closest_est_dist <= 160:
                self.path.clear()
                self.current_action = "Assault Firing"
                if self.shoot_cooldown <= 0:
                    self._fire_at(aim_pos, projectiles_group, fire_prob=0.65)
                    self.shoot_cooldown = 35
            elif self.shoot_cooldown <= 0:
                self.current_action = "Engaging"
                self._fire_at(aim_pos, projectiles_group, fire_prob=0.4)
                self.shoot_cooldown = 48
        elif self.spotted_targets:
            self.current_action = "Tracking Target"
        elif self.path:
            self.current_action = f"Advancing ({self.move_order})"
        else:
            self.current_action = "Observing"

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

    def draw(self, surface, camera_offset=(0, 0), debug_mode=False):
        ox, oy = int(camera_offset[0]), int(camera_offset[1])

        for marker in self.local_casualties:
            marker.draw(surface, camera_offset)

        if self.total_health() <= 0:
            return

        if self.selected and self.path:
            pts = [pygame.Vector2(self.pos.x - ox, self.pos.y - oy)] + [
                pygame.Vector2(gx * CELL_SIZE + CELL_SIZE // 2 - ox, gy * CELL_SIZE + CELL_SIZE // 2 - oy)
                for gx, gy in self.path
            ]
            if len(pts) > 1:
                pygame.draw.lines(surface, (230, 195, 75), False, pts, 2)

        if debug_mode:
            spot_r = int(self.spotting_limit * self.get_binoculars_spot_bonus())
            pygame.draw.circle(surface, (90, 120, 90), (int(self.pos.x - ox), int(self.pos.y - oy)), spot_r, 1)
        if self.selected or debug_mode:
            for data in self.spotted_targets.values():
                ep = data["estimated_pos"]
                ex, ey = int(ep.x - ox), int(ep.y - oy)
                pygame.draw.circle(surface, (235, 190, 75), (ex, ey), 7, 1)
                pygame.draw.line(surface, (235, 190, 75), (ex - 5, ey), (ex + 5, ey), 1)
                pygame.draw.line(surface, (235, 190, 75), (ex, ey - 5), (ex, ey + 5), 1)
 
        for idx, s in enumerate(self.members):
            spos = self.get_soldier_world_pos(idx)
            sx, sy = int(spos.x - ox), int(spos.y - oy)

            base_color = COLOR_BLUE_SOLDIER if self.team == "blue" else COLOR_RED_SOLDIER
            if self.suppression > 50:
                base_color = COLOR_SUPPRESSED_TINT

            pygame.draw.circle(surface, base_color, (sx, sy), 5)
            pygame.draw.circle(surface, (20, 18, 20), (sx, sy), 6, 1)

            if self.selected:
                pygame.draw.circle(surface, COLOR_SELECTED_RING, (sx, sy), 9, 1)

        if self.selected:

            pygame.draw.circle(surface, (220, 50, 60), (int(self.pos.x - ox), int(self.pos.y - oy)), self.collision_radius, 1)

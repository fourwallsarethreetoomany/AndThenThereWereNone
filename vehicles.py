# vehicles.py defines vehicles and behavior duh!
import math
import random
import pygame

try:
    from setup import CELL_SIZE
except ImportError:
    CELL_SIZE = 150

from combat import Projectile, MuzzleFlash, Explosion
from unit import Soldier, Squad


class ImageLoader: # leave it here for now, i have no idea what im doing!!!!!

    def __init__(self):
        self._cache = {}

    def get_image(self, path, scale_size=None):
        key = (path, scale_size)

        if key not in self._cache:
            img = pygame.image.load(path).convert_alpha()
            if scale_size:
                img = pygame.transform.scale(img, scale_size)
            self._cache[key] = img

        return self._cache[key]

class SubSystem:
    def __init__(self, x, y, integrity=0, status="ON", team="blue"):
        super().__init__()
        self.team = team
        self.x = x
        self.y = y
        self.integrity = integrity
        self.status = status

class Engine(SubSystem):
    def __init__(self, x, y, horsepower, integrity=100):
        super().__init__(x, y, integrity=integrity)
        self.horsepower = horsepower

class Vehicle(pygame.sprite.Sprite): 
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, angle=0, team="blue",
                 req_points=12345, rarity_points=12345, is_full_unit=False, year_unlock=1985, crew_member=None,
                 effects_group=None):
        super().__init__()
        self.angle = angle
        self.turret_angle = angle
        self.team = team
        self.original_image = image_surface if image_surface else self._build_default_surface(team)
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration_magnitude = 0.0
        self.req_points = req_points * (3 if is_full_unit else 1)
        self.rarity_points = rarity_points * (2 if is_full_unit else 1)
        self.is_full_unit = is_full_unit
        self.year_unlock = year_unlock
        self.crew_member = crew_member

        self.gx = int(x // CELL_SIZE)
        self.gy = int(y // CELL_SIZE)
        self.path = []
        self.move_order = "Normal"
        self.base_speed = max(1.1, min(3.0, max_speed * 0.028))
        self.speed = self.base_speed
        self.selected = False
        self.collision_radius = 25

        self.unit_name = self.__class__.__name__
        self.hp = 200
        self.max_hp = 200
        self.nominal_armor = 15
        self.suppression = 0.0
        self.under_fire = False
        self.current_action = "Observing"
        self.shoot_cooldown = random.randint(10, 30)
        self.effects_group = effects_group

        self.spotting_limit = 620.0
        self.experience = 1.0
        self.has_rangefinder = True
        self.range_estimate_interval = 600
        self.spotted_targets = {}

        self.weapon_name = "Coaxial MG"
        self.weapon_range = 420.0
        self.fire_rate = 30
        self.caliber = 7.62
        self.current_ammo = "Ball"
        self.ammo_types = ["Ball"]

        cmdr = Soldier(f"{self.unit_name} Cmdr", "Sergeant", self.weapon_name)
        self.squad = Squad(cmdr)
        self.squad.fireteams = [self]
        self.members = [cmdr]
        self.squad.add_member(cmdr)
        self.initial_member_count = 1
        self.crew_size = 1

    def _build_default_surface(self, team):
        surf = pygame.Surface((42, 26), pygame.SRCALPHA)
        hull_col = (55, 110, 185) if team == "blue" else (180, 50, 58)
        pygame.draw.rect(surf, hull_col, (3, 4, 32, 18), border_radius=3)
        pygame.draw.rect(surf, (20, 20, 22), (3, 4, 32, 18), 2, border_radius=3)
        pygame.draw.line(surf, (35, 35, 38), (22, 13), (41, 13), 3)
        return surf

    def total_health(self):
        return self.hp

    def avg_morale(self):
        return max(0, 100 - int(self.suppression * 0.7))

    def set_order(self, order_name):
        self.move_order = order_name
        if order_name == "Normal":
            self.speed = self.base_speed
        elif order_name == "Quick":
            self.speed = self.base_speed * 1.35
        elif order_name == "Fast":
            self.speed = self.base_speed * 1.6
        elif order_name == "Sneak":
            self.speed = self.base_speed * 0.65
        elif order_name == "Assault":
            self.speed = self.base_speed * 1.15
        elif order_name == "Halt":
            self.path.clear()

    def compute_range_estimate(self, enemy):
        real_range = self.pos.distance_to(enemy.pos)
        error_pixels = 5.0 * self.experience * ( 1 + (real_range / 2000.0))
        sign = random.choice([-1, 1])
        estimated_range = max(0.0, real_range + sign * error_pixels)

        direction = enemy.pos - self.pos
        if direction.length_squared() > 0:
            estimated_pos = self.pos + direction.normalize() * estimated_range
        else:
            estimated_pos = pygame.Vector2(self.pos)

        return real_range, estimated_range, estimated_pos

    def update_tacai_spotting(self, grid, all_units, force_estimate=False):
        obs_cell = grid.get_cell(self.gx, self.gy)
        spot_bonus = getattr(obs_cell, "spot_bonus", 1.0) if obs_cell else 1.0

        active_enemies = set()
        for other in all_units:
            if other.team == self.team or other.total_health() <= 0:
                continue
            active_enemies.add(other)

            real_range = self.pos.distance_to(other.pos)
            tgt_cell = grid.get_cell(other.gx, other.gy)
            concealment = getattr(tgt_cell, "concealment", 0.0) if tgt_cell else 0.0
            effective_limit = self.spotting_limit * spot_bonus * max(0.25, 1.0 - concealment)

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

    def choose_ammo_for_target(self, target):
        return self.current_ammo

    def get_ammo_profile(self):
        return self.caliber, self.current_ammo, 12, 0

    def apply_damage(self, caliber, projectile_type, soldier_index=None, penetration=0):
        if self.hp <= 0:
            return
        if penetration <= 0:
            if caliber >= 100:
                penetration = 25 if projectile_type == "HE" else (280 if projectile_type == "HEAT" else 220)
            elif caliber >= 14:
                penetration = 32
            else:
                penetration = 8

        self.under_fire = True
        if projectile_type == "HE":
            self.suppression = min(100.0, self.suppression + 28.0)
            dmg = 18 if self.nominal_armor >= 50 else 95
            self.hp = max(0, self.hp - dmg)
        elif penetration >= self.nominal_armor:
            self.suppression = min(100.0, self.suppression + 35.0)
            dmg = max(25, int(caliber * (1.8 if projectile_type in ("AP", "HEAT") else 2.2)))
            self.hp = max(0, self.hp - dmg)
        else:
            self.suppression = min(100.0, self.suppression + 6.0)

        if self.hp <= 0:
            if self.effects_group is not None:
                self.effects_group.add(Explosion(self.pos, max_radius=48, duration=28))
            for m in self.members:
                m.condition = 0

    def update(self, grid, all_units, projectiles_group):
        if self.hp <= 0:
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
            self.suppression = max(0.0, self.suppression - 0.15)

        self.update_tacai_spotting(grid, all_units)

        target_enemy = None
        target_data = None
        closest_est_dist = 9999.0
        for enemy, data in self.spotted_targets.items():
            est_dist = data["estimated_range"]
            if est_dist <= self.weapon_range and est_dist < closest_est_dist:
                closest_est_dist = est_dist
                target_enemy = enemy
                target_data = data

        if target_enemy and target_data:
            aim_pos = target_data["estimated_pos"]
            self.choose_ammo_for_target(target_enemy)
            vec_to_tgt = aim_pos - self.pos
            if vec_to_tgt.length_squared() > 0:
                self.turret_angle = math.degrees(math.atan2(vec_to_tgt.y, vec_to_tgt.x))
            self.current_action = f"Engaging [{self.current_ammo}]"

            if self.shoot_cooldown <= 0:
                cal, p_type, pen, blast_r = self.get_ammo_profile()
                dir_vec = vec_to_tgt.normalize() if vec_to_tgt.length_squared() > 0 else pygame.Vector2(1, 0)
                muzzle_pos = self.pos + dir_vec * 24
                projectiles_group.add(
                    Projectile(
                        muzzle_pos.x, muzzle_pos.y, 2, aim_pos, 0,
                        cal, p_type, self.team,
                        penetration=pen, blast_radius=blast_r, effects_group=self.effects_group
                    )
                )
                if self.effects_group is not None:
                    flash_sz = 18 if cal >= 50 else 11
                    self.effects_group.add(MuzzleFlash(muzzle_pos, dir_vec, size=flash_sz, duration=8 if cal >= 50 else 5))
                self.shoot_cooldown = self.fire_rate
        elif self.spotted_targets:
            self.current_action = "Tracking Target"
        elif self.path:
            self.current_action = f"Moving ({self.move_order})"
        else:
            self.current_action = "Observing"

        if self.path:
            nxt_gx, nxt_gy = self.path[0]
            target_pos = grid.grid_to_world_center(nxt_gx, nxt_gy)
            vec = target_pos - self.pos
            dist = vec.length()
            if vec.length_squared() > 0:
                self.angle = math.degrees(math.atan2(vec.y, vec.x))
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

        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def draw(self, surface, camera_offset=(0, 0), debug_mode=False):
        ox, oy = int(camera_offset[0]), int(camera_offset[1])
        sx, sy = int(self.pos.x - ox), int(self.pos.y - oy)

        if self.hp <= 0:
            pygame.draw.circle(surface, (28, 24, 24), (sx, sy), 18)
            pygame.draw.circle(surface, (60, 42, 42), (sx, sy), 18, 2)
            return

        if self.selected and self.path:
            pts = [pygame.Vector2(sx, sy)] + [
                pygame.Vector2(gx * CELL_SIZE + CELL_SIZE // 2 - ox, gy * CELL_SIZE + CELL_SIZE // 2 - oy)
                for gx, gy in self.path
            ]
            if len(pts) > 1:
                pygame.draw.lines(surface, (230, 195, 75), False, pts, 2)

        if debug_mode:
            pygame.draw.circle(surface, (90, 130, 110), (sx, sy), int(self.spotting_limit), 1)
        if self.selected or debug_mode:
            for data in self.spotted_targets.values():
                ep = data["estimated_pos"]
                ex, ey = int(ep.x - ox), int(ep.y - oy)
                pygame.draw.circle(surface, (235, 190, 75), (ex, ey), 8, 1)
                pygame.draw.line(surface, (235, 190, 75), (ex - 6, ey), (ex + 6, ey), 1)
                pygame.draw.line(surface, (235, 190, 75), (ex, ey - 6), (ex, ey + 6), 1)

        surface.blit(self.image, self.rect.move(-ox, -oy))

        rad = math.radians(self.turret_angle)
        barrel_len = 26 if self.caliber >= 50 else 18
        bx = sx + int(math.cos(rad) * barrel_len)
        by = sy + int(math.sin(rad) * barrel_len)
        pygame.draw.line(surface, (30, 32, 30), (sx, sy), (bx, by), 4 if self.caliber >= 50 else 2)

        if self.selected:
            pygame.draw.circle(surface, (240, 205, 90), (sx, sy), self.collision_radius + 4, 2)

    def move(self):
        pass
 

class WheeledVehicle(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, req_points=70, rarity_points=10, is_full_unit=False, year_unlock=1985, crew_member=None, effects_group=None):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, req_points=req_points, rarity_points=rarity_points, is_full_unit=is_full_unit, effects_group=effects_group)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}
        self.crew = crew_member if crew_member else {}

class TrackedVehicle(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, req_points=150, rarity_points=30, is_full_unit=False, effects_group=None):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, req_points=req_points, rarity_points=rarity_points, is_full_unit=is_full_unit, effects_group=effects_group)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}

class HalfTracked(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, req_points=80, rarity_points=15, is_full_unit=False, effects_group=None):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, req_points=req_points, rarity_points=rarity_points, is_full_unit=is_full_unit, effects_group=effects_group)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}

class ZIL131(WheeledVehicle):
    def __init__(self, x, y, image_surface=None, length=7.0, height=2.4, max_speed=80, acceleration=1.2, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False, effects_group=None):
        truck_armor = {'front_window': 30, 'front_hull': 5, 'side_hull': 3, 'rear_hull': 2, 'roof': 0}
        truck_angle = {'window_angle': 5, 'front_angle': 0, 'side_angle': 0, 'rear_angle': 0, 'roof_angle': 0}
        truck_material = {'glass', 'steel'}
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=truck_armor, angle_dict=truck_angle, materials_dict=truck_material, req_points=40, rarity_points=5, is_full_unit=is_full_unit, effects_group=effects_group)

class BRDM(WheeledVehicle): 
    def __init__(self, x, y, image_surface=None, length=5.75, height=2.31, max_speed=100, acceleration=1.8, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False, effects_group=None):
        brdm_armor = {'nose_armor': 14, 'front_turret': 10, 'front_hull': 14, 'side_armor': 7, 'roof_armor': 7}
        brdm_angle = {'nose_armor': 40, 'font_lower_angle': 35, 'front_upper_angle': 30, 'side_angle': 45, 'rear_angle': 0}
        if image_surface is None:
            image_surface = self._make_brdm_sprite(team)
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=brdm_armor, angle_dict=brdm_angle, req_points=75, rarity_points=0, is_full_unit=is_full_unit, effects_group=effects_group)
        self.unit_name = "BRDM-2"
        self.hp = 180
        self.max_hp = 180
        self.nominal_armor = 14
        self.spotting_limit = 680.0
        self.weapon_name = "14.5mm KPVT"
        self.weapon_range = 500.0
        self.fire_rate = 24
        self.caliber = 14.5
        self.ammo_types = ["AP-I"]
        self.current_ammo = "AP-I"
        self.collision_radius = 22
        self.members = [
            Soldier("BRDM-2 Commander", "Sergeant", "14.5mm KPVT"),
            Soldier("BRDM-2 Driver", "Corporal", "AK-74"),
        ]
        self.squad.leader = self.members[0]
        self.squad.members = list(self.members)
        self.initial_member_count = len(self.members)

    def _make_brdm_sprite(self, team):
        surf = pygame.Surface((40, 26), pygame.SRCALPHA)
        body_col = (52, 112, 185) if team == "blue" else (182, 46, 56)
        for wx in (6, 26):
            pygame.draw.rect(surf, (22, 22, 24), (wx, 1, 8, 4))
            pygame.draw.rect(surf, (22, 22, 24), (wx, 21, 8, 4))
        pygame.draw.polygon(surf, body_col, [(4, 6), (28, 5), (37, 13), (28, 21), (4, 20)])
        pygame.draw.polygon(surf, (22, 22, 26), [(4, 6), (28, 5), (37, 13), (28, 21), (4, 20)], 2)
        pygame.draw.circle(surf, (38, 46, 52), (19, 13), 6)
        pygame.draw.circle(surf, (20, 20, 22), (19, 13), 6, 1)
        return surf

    def get_ammo_profile(self):
        return 14.5, "AP-I", 32, 0
 
 
BRDM2 = BRDM

class Zachlam(HalfTracked):
    def __init__(self, x, y, image_surface=None, length=6.0, height=2.2, max_speed=72, acceleration=1.4, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False, effects_group=None):
        zachlam_armor = {'nose_armor': 14, 'front_turret': 10, 'front_hull': 14, 'side_armor': 7, 'roof_armor': 7}
        zachlam_angle = {'nose_armor': 40, 'front_lower_angle': 35, 'front_upper_angle': 30, 'side_angle': 45, 'rear_angle': 0}
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=zachlam_armor, angle_dict=zachlam_angle, req_points=65, rarity_points=12, is_full_unit=is_full_unit, effects_group=effects_group)

class T55(TrackedVehicle): # a lot of palceholders in all of these 
    def __init__(self, x, y, image_surface=None, length=6.0, height=2.35, max_speed=50, acceleration=1.4, azimuth=0, team="A", armor_dict=None, angle_dict=None, is_full_unit=False, effects_group=None):
        t55_armor = {"front_turret": 99, "front_hull": 203}
        t55_angle = {"front_turret": 5, "front_hull": 45}
        if image_surface is None:
            image_surface = self._make_t55_sprite(team)
        super().__init__(x, y, 9.0, 2.4, max_speed, 1.5, image_surface, azimuth=azimuth, team=team, armor_dict=t55_armor, angle_dict=t55_angle, req_points=225, rarity_points=25, is_full_unit=is_full_unit, effects_group=effects_group)
        self.unit_name = "T-55A"
        self.hp = 450
        self.max_hp = 450
        self.nominal_armor = 150
        self.spotting_limit = 640.0
        self.weapon_name = "100mm D-10T2S"
        self.weapon_range = 620.0
        self.fire_rate = 140
        self.caliber = 100
        self.ammo_types = ["AP", "HEAT", "HE"]
        self.current_ammo = "AP"
        self.collision_radius = 27
        self.members = [
            Soldier("T-55 Commander", "Sergeant", "100mm D-10T2S"),
            Soldier("T-55 Gunner", "Corporal", "100mm D-10T2S"),
            Soldier("T-55 Loader", "Private", "7.62mm PKT"),
            Soldier("T-55 Driver", "Private", "Driver"),
        ]
        self.squad.leader = self.members[0]
        self.squad.members = list(self.members)
        self.initial_member_count = len(self.members)

    def _make_t55_sprite(self, team):
        surf = pygame.Surface((48, 32), pygame.SRCALPHA)
        hull_col = (46, 98, 165) if team == "blue" else (165, 42, 48)
        pygame.draw.rect(surf, (24, 24, 26), (3, 2, 42, 5))
        pygame.draw.rect(surf, (24, 24, 26), (3, 25, 42, 5))
        pygame.draw.rect(surf, hull_col, (5, 6, 38, 20), border_radius=2)
        pygame.draw.rect(surf, (18, 20, 22), (5, 6, 38, 20), 2, border_radius=2)
        pygame.draw.circle(surf, (65, 75, 72) if team == "blue" else (95, 42, 46), (24, 16), 9)
        pygame.draw.circle(surf, (20, 20, 22), (24, 16), 9, 2)
        return surf

    def choose_ammo_for_target(self, target):
        if isinstance(target, TrackedVehicle):
            self.current_ammo = "AP"
        elif isinstance(target, Vehicle):
            self.current_ammo = "HEAT"
        else:
            self.current_ammo = "HE"
        return self.current_ammo

    def get_ammo_profile(self):
        if self.current_ammo == "AP":
            return 100, "AP", 220, 0
        elif self.current_ammo == "HEAT":
            return 100, "HEAT", 280, 24
        else:
            return 100, "HE", 25, 48
    # [EDIT END]

class T62(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t62_armor = {"front_turret": 99, "front_hull": 203}
        t62_angle = {"front_turret": 5, "front_hull": 45}
        t62_material = {"front_turret": "HHA"}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t62_armor, angle_dict=t62_angle, materials_dict=t62_material, req_points=290, rarity_points=0, is_full_unit=is_full_unit)

class T62_1972(T62):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t62_armor = {"front_turret": 102, "front_hull": 242}
        t62_angle = {"front_turret": 5, "front_hull": 45}
        TrackedVehicle.__init__(self, x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t62_armor, angle_dict=t62_angle, req_points=290, rarity_points=0, is_full_unit=is_full_unit)

class T64(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t64_armor = {"front_turret": 99, "front_hull": 203}
        t64_angle = {"front_turret": 5, "front_hull": 45}
        t64_material = {"front_armor": "Combination K", "front_turret": "Combination K"}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t64_armor, angle_dict=t64_angle, materials_dict=t64_material, req_points=340, rarity_points=45, is_full_unit=is_full_unit)

class T72_Ural(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t72_armor = {"front_turret": 99, "front_hull": 203}
        t72_angle = {"front_turret": 5, "front_hull": 45}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t72_armor, angle_dict=t72_angle, req_points=355, rarity_points=10, is_full_unit=is_full_unit)

class T80(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t80_armor = {"front_turret": 99, "front_hull": 203}
        t80_angle = {"front_turret": 5, "front_hull": 45}
        t80_material = {"front_armor": "Combination K ERA"}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t80_armor, angle_dict=t80_angle, req_points=320, rarity_points=90, is_full_unit=is_full_unit)

class Tank_122(TrackedVehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=150, rarity_points=30, is_full_unit=is_full_unit)


class Prototype_1221(Tank_122):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=150, rarity_points=30, is_full_unit=is_full_unit)

class Prototype_1222(Tank_122):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=150, rarity_points=30, is_full_unit=is_full_unit)


class Prototype_1224(Tank_122):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=150, rarity_points=30, is_full_unit=is_full_unit)

class XM1(TrackedVehicle): #placeholder prototype abrams 
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=340, rarity_points=325, is_full_unit=is_full_unit)


class XM1_Chrysler(XM1):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=340, rarity_points=325, is_full_unit=is_full_unit)


class M1(TrackedVehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="a", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict, angle_dict, materials_dict, req_points=385, rarity_points=100, is_full_unit=is_full_unit)


class Tiran5(T55):
    pass

class Type_59(T55):
    pass

# [DELETE] Removed incomplete dangling 'class ' declaration

class Magach3(TrackedVehicle):
    pass

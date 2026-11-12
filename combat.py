import math
import random
import pygame

# Dark Crimson & Combat Palette
COLOR_TRACER_BALLISTIC = (255, 230, 140)
COLOR_TRACER_CRIMSON   = (255, 60, 70)
COLOR_BURST_FLASH      = (255, 180, 80)
COLOR_EXPLOSION_RED    = (190, 32, 42)

class DamageManager:
    def __init__(self):
        pass

    def update(self, projectiles_group, potential_targets):
        for projectile in list(projectiles_group):
            for target in potential_targets:
                # Do not hit friendly forces
                if getattr(projectile, "owner_value", None) == getattr(target, "team", None):
                    continue

                t_pos = target.pos if hasattr(target, "pos") else pygame.Vector2(target.rect.center)
                t_radius = getattr(target, "collision_radius", 18)
                t_min_height = getattr(target, "min_height", 0)
                t_max_height = getattr(target, "max_height", 12)

                # Check proximity to team center or individual soldiers
                hit_detected = False
                hit_soldier_idx = None

                # Check individual soldiers if the target supports individual modeling
                if hasattr(target, "members") and hasattr(target, "get_soldier_world_pos"):
                    for s_idx, soldier in enumerate(target.members):
                        if soldier.condition <= 0:
                            continue
                        spos = target.get_soldier_world_pos(s_idx)
                        if projectile.pos.distance_to(spos) <= 10:
                            if t_min_height <= projectile.z_mimic <= t_max_height:
                                hit_detected = True
                                hit_soldier_idx = s_idx
                                break

                # Fallback to team bounding radius
                if not hit_detected and projectile.pos.distance_to(t_pos) <= t_radius:
                    if t_min_height <= projectile.z_mimic <= t_max_height:
                        hit_detected = True

                if hit_detected:
                    self.route_damage(target, projectile, hit_soldier_idx)
                    projectile.kill()
                    break

    def route_damage(self, target, projectile, soldier_idx=None):
        if hasattr(target, "apply_damage"):
            target.apply_damage(
                getattr(projectile, "caliber", 7.62),
                getattr(projectile, "projectile_type", "ball"),
                soldier_index=soldier_idx
            )


class CollisionManager:
    def __init__(self, impassable_mask=None):
        self.impassable_mask = impassable_mask

    def update(self, units_group, buildings_group):
        self.check_unit_building_collisions(units_group, buildings_group)
        self.check_unit_unit_collisions(units_group)

    def check_unit_building_collisions(self, units_group, buildings_group):
        for unit in units_group:
            if not hasattr(unit, "rect") or unit.rect is None:
                continue
            hit_buildings = pygame.sprite.spritecollide(unit, buildings_group, False)
            if hit_buildings and hasattr(unit, "resolve_collision"):
                unit.resolve_collision(hit_buildings)

    def check_unit_unit_collisions(self, units_group):
        units_list = list(units_group)
        for i in range(len(units_list)):
            for j in range(i + 1, len(units_list)):
                u1 = units_list[i]
                u2 = units_list[j]
                if not hasattr(u1, "pos") or not hasattr(u2, "pos"):
                    continue

                min_dist = getattr(u1, "collision_radius", 16) + getattr(u2, "collision_radius", 16)
                disp = u1.pos - u2.pos
                dist = disp.length()
                if 0 < dist < min_dist:
                    overlap = (min_dist - dist) * 0.5
                    push = disp.normalize() * overlap
                    u1.pos += push
                    u2.pos -= push


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, z_mimic, target_pos, dir_angle, caliber, projectile_type, owner_value):
        super().__init__()
        self.pos = pygame.Vector2(x, y)
        self.z_mimic = z_mimic
        self.owner_value = owner_value
        self.caliber = caliber
        self.projectile_type = projectile_type
        self.dir = dir_angle

        direction = target_pos - self.pos
        if direction.length_squared() > 0:
            speed = 18.0 if caliber < 20 else 12.0
            # Slight dispersion based on distance
            spread_angle = random.uniform(-0.03, 0.03)
            vel = direction.normalize().rotate_rad(spread_angle) * speed
            self.velocity = vel
        else:
            self.velocity = pygame.Vector2(0, 0)

        self.lifetime = 140

        # Tracer visual
        self.image = pygame.Surface((6, 6), pygame.SRCALPHA)
        tracer_color = COLOR_TRACER_CRIMSON if owner_value == "red" else COLOR_TRACER_BALLISTIC
        pygame.draw.circle(self.image, tracer_color, (3, 3), 2)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


class BallisticProjectile(Projectile):
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, caliber, projectile_type, owner_value):
        super().__init__(x, y, z_start, target_pos, 0, caliber, projectile_type, owner_value)
        self.vz = vz_initial
        self.gravity = gravity

    def update(self):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.z_mimic += self.vz
        self.vz -= self.gravity
        self.lifetime -= 1

        if self.z_mimic <= 0:
            self.z_mimic = 0
            self.detonate()
            self.kill()
        elif self.lifetime <= 0:
            self.kill()

    def detonate(self):
        pass


class AviationBomb(BallisticProjectile):
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type="HE"):
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, 250, projectile_type, owner_value)
        self.explosive_filling = explosive_filling

class FAB250(AviationBomb):
    def __init__(self, x, y, z_start, target_pos, vz_initial=0, gravity=0.4, owner_value="blue"):
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, owner_value, 250, "HE")

class FAB500(AviationBomb):
    def __init__(self, x, y, z_start, target_pos, vz_initial=0, gravity=0.45, owner_value="blue"):
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, owner_value, 500, "HE")

class BigShell(BallisticProjectile):
    def __init__(self, x, y, target_pos, owner_is_player=True):
        owner_val = "blue" if owner_is_player else "red"
        super().__init__(x, y, 40, target_pos, 1.2, 0.08, 122, "HE", owner_val)
        self.damage = 180



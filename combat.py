import math
import random
import pygame

# Color list, to-do: smoke, muzzle flash, etc.
COLOR_TRACER_BALLISTIC = (255, 230, 140)
COLOR_TRACER_CRIMSON   = (255, 60, 70)
COLOR_BURST_FLASH      = (255, 180, 80)
COLOR_EXPLOSION_RED    = (190, 32, 42)


class MuzzleFlash(pygame.sprite.Sprite):
    def __init__(self, pos, direction_vec, size=8, duration=6):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.direction = direction_vec.normalize() if direction_vec.length_squared() > 0 else pygame.Vector2(1, 0)
        self.size = size
        self.duration = duration
        self.age = 0
        surf_dim = size * 3
        self.image = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self._redraw()

    def _redraw(self):
        self.image.fill((0, 0, 0, 0))
        alpha = max(30, int(255 * (1.0 - self.age / max(1, self.duration))))
        c = pygame.Vector2(self.image.get_width() // 2, self.image.get_height() // 2)
        tip = c + self.direction * (self.size * 1.35)
        perp = pygame.Vector2(-self.direction.y, self.direction.x) * (self.size * 0.55)
        poly = [c - perp * 0.5, tip, c + perp * 0.5]
        pygame.draw.polygon(self.image, (255, 195, 70, alpha), poly)
        pygame.draw.circle(self.image, (255, 245, 180, alpha), (int(c.x), int(c.y)), max(2, self.size // 3))

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.kill()
        else:
            self._redraw()


class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos, max_radius=38, duration=22):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.max_radius = max_radius
        self.duration = duration
        self.age = 0
        dim = max_radius * 2 + 8
        self.image = pygame.Surface((dim, dim), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self._redraw()

    def _redraw(self):
        self.image.fill((0, 0, 0, 0))
        t = self.age / max(1, self.duration)
        cur_r = max(4, int(self.max_radius * (0.35 + 0.65 * t)))
        alpha = max(0, int(235 * (1.0 - t)))
        cx = self.image.get_width() // 2
        cy = self.image.get_height() // 2

        pygame.draw.circle(self.image, (85, 75, 75, int(alpha * 0.65)), (cx, cy), cur_r)
        pygame.draw.circle(self.image, (*COLOR_EXPLOSION_RED, alpha), (cx, cy), max(2, int(cur_r * 0.72)))
        if t < 0.65:
            core_alpha = max(0, int(255 * (1.0 - t / 0.65)))
            pygame.draw.circle(self.image, (*COLOR_BURST_FLASH, core_alpha), (cx, cy), max(2, int(cur_r * 0.42)))

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.kill()
        else:
            self._redraw()


class DamageManager:
    def __init__(self):
        pass

    def update(self, projectiles_group, potential_targets, effects_group=None):
        for projectile in list(projectiles_group):
            for target in potential_targets:
                if getattr(projectile, "owner_value", None) == getattr(target, "team", None):
                    continue

                if hasattr(target, "total_health") and target.total_health() <= 0:
                    continue

                t_pos = target.pos if hasattr(target, "pos") else pygame.Vector2(target.rect.center)
                t_radius = getattr(target, "collision_radius", 18)
                t_min_height = getattr(target, "min_height", 0)
                t_max_height = getattr(target, "max_height", 12)

                hit_detected = False
                hit_soldier_idx = None

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

                if not hit_detected and projectile.pos.distance_to(t_pos) <= t_radius:
                    if t_min_height <= projectile.z_mimic <= t_max_height:
                        hit_detected = True

                if hit_detected:
                    self.route_damage(target, projectile, hit_soldier_idx)
                    self.trigger_impact_effects(projectile, potential_targets, effects_group, primary_target=target)
                    projectile.kill()
                    break

    def trigger_impact_effects(self, projectile, potential_targets, effects_group, primary_target=None):
        p_type = getattr(projectile, "projectile_type", "ball")
        blast_r = getattr(projectile, "blast_radius", 0)
        caliber = getattr(projectile, "caliber", 7.62)

        if effects_group is not None:
            if p_type == "HE":
                effects_group.add(Explosion(projectile.pos, max_radius=max(36, blast_r), duration=22))
            elif p_type == "HEAT":
                effects_group.add(Explosion(projectile.pos, max_radius=max(24, blast_r), duration=16))
            elif caliber >= 14:
                effects_group.add(Explosion(projectile.pos, max_radius=12, duration=8))

        if p_type in ("HE", "HEAT") and blast_r > 0:
            for other in potential_targets:
                if other is primary_target:
                    continue
                if getattr(projectile, "owner_value", None) == getattr(other, "team", None):
                    continue
                if hasattr(other, "total_health") and other.total_health() <= 0:
                    continue
                opos = other.pos if hasattr(other, "pos") else pygame.Vector2(other.rect.center)
                if projectile.pos.distance_to(opos) <= blast_r:
                    self.route_damage(other, projectile, None)

    def route_damage(self, target, projectile, soldier_idx=None):
        if hasattr(target, "apply_damage"):
            try:
                target.apply_damage(
                    getattr(projectile, "caliber", 7.62),
                    getattr(projectile, "projectile_type", "ball"),
                    soldier_index=soldier_idx,
                    penetration=getattr(projectile, "penetration", 0),
                )
            except TypeError:
                target.apply_damage(
                    getattr(projectile, "caliber", 7.62),
                    getattr(projectile, "projectile_type", "ball"),
                    soldier_index=soldier_idx,
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
    # [EDIT START] Added penetration, blast_radius, effects_group, and explosive detonation at target_pos
    def __init__(self, x, y, z_mimic, target_pos, dir_angle, caliber, projectile_type, owner_value,
                 penetration=0, blast_radius=0, effects_group=None):
        super().__init__()
        self.pos = pygame.Vector2(x, y)
        self.target_pos = pygame.Vector2(target_pos)
        self.z_mimic = z_mimic
        self.owner_value = owner_value
        self.caliber = caliber
        self.projectile_type = projectile_type
        self.dir = dir_angle
        self.penetration = penetration
        self.blast_radius = blast_radius
        self.effects_group = effects_group
        self.is_explosive = projectile_type in ("HE", "HEAT")

        direction = self.target_pos - self.pos
        if direction.length_squared() > 0:
            speed = 18.0 if caliber < 20 else 14.0
            spread_angle = random.uniform(-0.03, 0.03)
            vel = direction.normalize().rotate_rad(spread_angle) * speed
            self.velocity = vel
        else:
            self.velocity = pygame.Vector2(0, 0)

        self.lifetime = 140

        if caliber >= 50:
            self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
            tracer_color = (255, 160, 75) if owner_value == "red" else (255, 235, 130)
            pygame.draw.circle(self.image, tracer_color, (5, 5), 4)
        elif caliber >= 14:
            self.image = pygame.Surface((8, 8), pygame.SRCALPHA)
            tracer_color = (255, 95, 75) if owner_value == "red" else (255, 220, 110)
            pygame.draw.circle(self.image, tracer_color, (4, 4), 3)
        else:
            self.image = pygame.Surface((6, 6), pygame.SRCALPHA)
            tracer_color = COLOR_TRACER_CRIMSON if owner_value == "red" else COLOR_TRACER_BALLISTIC
            pygame.draw.circle(self.image, tracer_color, (3, 3), 2)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self, potential_targets=None):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.lifetime -= 1

        if self.is_explosive and self.pos.distance_to(self.target_pos) <= max(10.0, self.velocity.length()):
            if self.effects_group is not None:
                self.effects_group.add(Explosion(self.pos, max_radius=max(24, self.blast_radius or 32), duration=20))
            if potential_targets is not None and self.blast_radius > 0:
                for tgt in potential_targets:
                    if getattr(tgt, "team", None) == self.owner_value:
                        continue
                    if hasattr(tgt, "total_health") and tgt.total_health() <= 0:
                        continue
                    tpos = tgt.pos if hasattr(tgt, "pos") else pygame.Vector2(tgt.rect.center)
                    if self.pos.distance_to(tpos) <= self.blast_radius and hasattr(tgt, "apply_damage"):
                        try:
                            tgt.apply_damage(self.caliber, self.projectile_type, penetration=self.penetration)
                        except TypeError:
                            tgt.apply_damage(self.caliber, self.projectile_type)
            self.kill()
            return

        if self.lifetime <= 0:
            self.kill()
    # [EDIT END]


class BallisticProjectile(Projectile):
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, caliber, projectile_type, owner_value):
        super().__init__(x, y, z_start, target_pos, 0, caliber, projectile_type, owner_value)
        self.vz = vz_initial
        self.gravity = gravity

    def update(self, potential_targets=None):
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

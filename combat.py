import math
import pygame
from setup import WIDTH, HEIGHT

class DamageManager:
    def __init__(self):
        pass
    def update (self, projectiles_group, potential_targets):
            for projectile in projectiles_group:
                for target in potential_targets:
                    if getattr(projectile, "owner_value", None) == getattr(
                            target, "team", None
                        ):
                            continue
                    t_pos = (
                        target.pos
                        if hasattr(target, "pos")
                        else pygame.Vector2(target.rect.center)
                    )
                    t_radius = getattr(target, "collision_radius", 15)
                    t_min_height = getattr(target, "min_height", 0)
                    t_max_height = getattr(target, "max_height", 10)
                    if projectile.pos.distance_to(t_pos) <= t_radius: 
                        if t_min_height <= projectile.z_mimic <= t_max_height:
                            self.route_damage(target, projectile)
                            projectile.kill()
                            break
    def route_damage(self, target, projectile): 
        if hasattr(target, "apply_damage"):
            target.apply_damage(
                getattr(projectile, "caliber", 0),
                getattr(projectile, "projectile_type", "unknown"),
            )
class CollisionManager:

    def __init__(self, impassable_mask=None):
        self.impassable_mask = impassable_mask  # Can be a surface mask, grid, or rect list

    def update(self, units_group, buildings_group): 
        self.check_unit_building_collisions(units_group, buildings_group)
        self.check_unit_unit_collisions(units_group)
        self.check_terrain_collisions(units_group)

    def check_unit_building_collisions(self, units_group, buildings_group): 
        for unit in units_group:
            if not hasattr(unit, "rect") or unit.rect is None:
                continue
            hit_buildings = pygame.sprite.spritecollide(
                unit, buildings_group, False
            )
            if hit_buildings: 
                if hasattr(unit, "resolve_collision"):
                    unit.resolve_collision(hit_buildings)

    def check_unit_unit_collisions(self, units_group): #unit collision
        units_list = list(units_group)
        for i in range(len(units_list)):
            for j in range(i + 1, len(units_list)):
                u1 = units_list[i]
                u2 = units_list[j]
                if u1.pos.distance_to(u2.pos) < (
                    getattr(u1, "collision_radius", 15)
                    + getattr(u2, "collision_radius", 15)
                ):
                    if hasattr(u1, "resolve_unit_collision"):
                        u1.resolve_unit_collision(u2)

    def check_terrain_collisions(self, units_group):
        if not self.impassable_mask:
            return

        for unit in units_group:
            x, y = int(unit.pos.x), int(unit.pos.y)
            if self.is_out_of_bounds(x, y) or self.is_impassable(x, y):
                if hasattr(unit, "handle_terrain_block"):
                    unit.handle_terrain_block()

    def is_out_of_bounds(self, x, y):
        return x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT

    def is_impassable(self, x, y):
        return False

class Projectile(pygame.sprite.Sprite): # all projectiles from bullets to shells and missiles
    def __init__(self, x, y, z_mimic, target_pos, dir, 
                 caliber, projectile_type, owner_value
                 ):
        super().__init__()
        self.pos = pygame.Vector2(x, y)
        self.z_mimic = z_mimic # projectiles get larger? the higher this is, used for artillery, thrown grenades, and aviation rockets/cannons, also used for detection of hits, when this is 0 then the damage script will be triggered
        self.owner_value = owner_value # friendly fire is disabled on easier difficuy
        self.caliber = caliber
        self.projectile_type = projectile_type
        self.dir = dir # direction the shell is moving at, we will mimic a parabola, this is more used for artillery and mortars.
        
        direction = target_pos - self.pos
        if direction.length_squared() > 0:
            self.velocity = direction.normalize() * (900 / 60)
        else:
            self.velocity = pygame.Vector2(0, 0)
        self.lifetime = 240  # Expires after4 seconds 

        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 235, 120), (2, 2), 2)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y))  
        self.lifetime -= 1
        if self.lifetime <= 0 or not (-200000 <= self.pos.x <= 200000 and -200000 <= self.pos.y <= 200000):
            self.kill()
class BallisticProjectile(Projectile):
    def __init__(self, x,y, z_start, target_pos, vz_initial, gravity, caliber, projectile_type, owner_value):
        super().__init__(x, y, z_start, target_pos, vz_initial, caliber, projectile_type, owner_value)
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
            self.projectile_detonate()  
            self.kill()  
        elif self.lifetime <= 0:
            self.kill()  
    def projectile_detonate(self):
        pass
def check_z_axis_collisions(projectiles_group, potential_targets):
    for projectile in projectiles_group:
        for target in potential_targets:
            if getattr(projectile, 'owner_value', None) == getattr(target, 'team', None):
                continue
            t_pos = target.pos if hasattr(target, 'pos') else pygame.Vector2(target.rect.center)
            t_radius = getattr(target, 'collision_radius', 15)
            t_min_height = getattr(target, 'min_height', 0)   
            t_max_height = getattr(target, 'max_height', 10)    

            if projectile.pos.distance_to(t_pos) <= t_radius:
                if t_min_height <= projectile.z_mimic <= t_max_height:
                    handle_hit(target, projectile)
                    projectile.kill()
                    break

def handle_hit(target, projectile):
    #placeholder routes the damage to the target
    if hasattr(target, 'apply_damage'):
        target.apply_damage(projectile.caliber, projectile.projectile_type)

class AviationBomb(BallisticProjectile):
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type):
       #placeholder
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, 500, projectile_type, owner_value)
        self.gravity = gravity
        self.explosive_filling = explosive_filling
        self.vz_initial = vz_initial

class FAB250(AviationBomb):
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type):
        #placeholder
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type)
        self.explosive_filling = 250
        self.gravity = 9.81

class FAB500(AviationBomb):
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type):
        #placeholder
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type)

class MK82(AviationBomb): # thankyouusayouaremybestfriend 
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type):
        #placeholder
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type)

class Bomb360_50(AviationBomb): #360 kg 
    def __init__(self, x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type):
        #placeholder
        super().__init__(x, y, z_start, target_pos, vz_initial, gravity, owner_value, explosive_filling, projectile_type)

class BigShell(BallisticProjectile):
    def __init__(self, x, y, target_pos, owner_is_player):
        super().__init__(x, y, 0, target_pos, 0, 0, 100, "HE", "player" if owner_is_player else "enemy")
        self.pos = pygame.Vector2(x, y)
        self.owner_is_player = owner_is_player
        self.damage = 160
        
        direction = target_pos - self.pos
        if direction.length_squared() > 0:
            self.velocity = direction.normalize() * 200
        else:
            self.velocity = pygame.Vector2(0, 0)
        self.lifetime = 150

    def update(self):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y)) # [ADDED] Sync rect
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


class AutoCannon: # all autocannons  
    def __init__(self, owner, offset=pygame.Vector2(0, 0), range_val=2000000, is_player=True, fire_rate=60): # [MODIFIED] added fire_rate parameter
        self.owner = owner
        self.offset = offset
        self.range = range_val
        self.cooldown = 0
        self.fire_rate = fire_rate #custom firerate 
        self.is_player = is_player
        self.current_target = None
        self.lock_timer = 0
        self.last_target_pos = None

    def get_world_pos(self):
        rad = math.radians(-self.owner.angle)
        rx = self.offset.x * math.cos(rad) - self.offset.y * math.sin(rad)
        ry = self.offset.x * math.sin(rad) + self.offset.y * math.cos(rad)
        return self.owner.pos + pygame.Vector2(rx, ry)




class LargeCannonWeapon: # ALLLLLLL High caliber guns
    def __init__(self, owner, offset=pygame.Vector2(0, 0), is_player=True):
        self.owner = owner
        self.offset = pygame.Vector2(offset)
        self.range = 150000
        self.cooldown = 0
        self.fire_rate = 85
        self.is_player = is_player
        self.last_target_pos = None

        self.slug_speed = 400.0

    def get_world_pos(self):
        rad = math.radians(-self.owner.angle)

        rx = (
            self.offset.x * math.cos(rad)
            - self.offset.y * math.sin(rad)
        )
        ry = (
            self.offset.x * math.sin(rad)
            + self.offset.y * math.cos(rad)
        )

        return self.owner.pos + pygame.Vector2(rx, ry)

import math
import random
import pygame
import asyncio
import heapq 
#import cocaine
# a few notes: each 5 pixels represents 1 meter,
pygame.init() 
HEIGHT = 800
WIDTH  = 1280
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
# 11/4/2026 finally made it actually run, imported heapq, added pathfinding, added testing squads, added ui, added a lot of placeholders for the grids (theyre just colors and stuff for now)
# 11/9/2026 going to add first mission and force selector
def clamp(val, min_val, max_val): # casemate and other weapons who have a limited field of fire such as bipod mg etc
    return max(min_val, min(val, max_val))
"""one little pigeon sittin in the tree, the rest got shot by KFC"""
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

    def update(self, potential_targets, shell_group):
        if self.cooldown > 0:
            self.cooldown -= 1

        mount_pos = self.get_world_pos()

        valid_targets = [
            t for t in potential_targets
            if t != self.owner
            and getattr(t, "is_player", None) != self.is_player
        ]

    

class Soldier:
    def __init__(self, name, rank, weapon="Rifle"): 
        self.name = name
        self.rank = rank
        self.weapon = weapon # [ADDED] Weapon type
        self.condition = 200        # health, 100 to incap, 0 mean dies. incaps can be stabalized with buddy aid, above 150 can be healed up and returned with a permament morale debuff for the match. Score calculated partially based on death and injury.
        self.morale = 100           # use transition matrix to determine probability that they will go from normal to shaken to suppressed to cowering or panicked
        self.is_pinned = False
        self.assigned_squad = None

class Squad:
    def __init__(self, squad_leader: Soldier):
        self.leader = squad_leader
        self.members = []
        self.formation_spread = 25  # spacing in pixels
        self.communication_link = False # normal squads don't get radios, if they do its on their vehicle. 
        self.fireteams = [] 

    def add_member(self, soldier: Soldier):
        soldier.assigned_squad = self
        self.members.append(soldier)

    def update_morale(self):
        # every so often call this
        if self.leader.morale < 30 or self.leader.condition <= 0:
            for member in self.members:
                member.morale -= 5
    def switch_state(self, soldier):
        if self.morale == 50: # use a matrix to determine probability of switching states.  
            pass #placeholder

class SubSystem:
    def __init__(self,x, y, integrity=0, status="ON", team="blue"):
        super().__init__() # [MODIFIED] fixed typo super().init__()
        self.team = team
        self.x = x   
        self.y = y  
        self.integrity = integrity #placeholder
        self.status = status ##placeholder
        


class Engine(SubSystem): #engine subsystem
    def __init__(self, x, y, horsepower, integrity=100):
        #placeholder
        super().__init__(x, y, integrity=integrity)
        self.horsepower = horsepower





class Vehicle(pygame.sprite.Sprite): #all vehicles use this class
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, angle=0, team="blue"):
        super().__init__()
        self.angle = angle
        self.team = team
        self.original_image = image_surface
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration_magnitude = 0.0

    def move(self):
        # placeholder
        pass
       
class WheeledVehicle(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}

class TrackedVehicle(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team)

        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}     
        self.armor_materials = materials_dict if materials_dict else {}
class HalfTracked(Vehicle): 
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}
class ZIL131(WheeledVehicle): #Truck, wheeled vehicle
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None):
        truck_armor = {
            'front_window': 30, 
            'front_hull': 5,
            'side_hull': 3,
            'rear_hull': 2,
            'roof': 0
        }

        truck_angle = {
            'window_angle': 5,
            'front_angle': 0,
            'side_angle': 0,
            'rear_angle': 0,
            'roof_angle': 0
        }

        truck_material = { #placeholder
            'glass',
            'steel'
        }
         
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=truck_armor, angle_dict=truck_angle, materials_dict=truck_material)
 
        
class BRDM(WheeledVehicle): #scout car, wheelev vehicle
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None):
        brdm_armor = {
            'nose_armor': 14,
            'front_turret':  10,
            'front_hull':  14,
            'side_armor': 7,
            'roof_armor': 7,
        }


        brdm_angle = {
            'nose_armor': 40,
            'font_lower_angle': 35,
            'front_upper_angle': 30,
            'side_angle': 45,
            'rear_angle': 0
        }


        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=brdm_armor, angle_dict=brdm_angle)

class Zachlam(HalfTracked): # Transport, half track
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None):
        Zachlam_armor = { #placeholder
            'nose_armor': 14,
            'front_turret':  10,
            'front_hull':  14,
            'side_armor': 7,
            'roof_armor': 7,
        }


        Zachlam_angle = {
            'nose_armor': 40,
            'front_lower_angle': 35, 
            'front_upper_angle': 30,
            'side_angle': 45,
            'rear_angle': 0
        }


        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=Zachlam_armor)

class T55(TrackedVehicle): #MBT Tracked
    def __init__(self, x , y, image_surface, team="A", armor_dict=None, angle_dict=None):
        t55_armor = {
            "front_turret":  99,
            "front_hull": 203
        }
        t55_angle = {
            "front_turret": 5,
            "front_hull": 45
        }
       #placeholder
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t55_armor, angle_dict=t55_angle)

class T62(TrackedVehicle): #MBT Tracked palceholder
    def __init__(self, x , y, image_surface, team="A", armor_dict=None, angle_dict=None):
        t55_armor = {
            "front_turret":  99,
            "front_hull": 203
        }
        t55_angle = {
            "front_turret": 5,
            "front_hull": 45
        }
        t55_material = {
            "front_turret": "HHA" #fact check this 
        }
       #placeholder
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t55_armor, angle_dict=t55_angle)
class T62_1972(T62): #MBT Tracked placeholder
    def __init__(self, x , y, image_surface, team="A", armor_dict=None, angle_dict=None):
        t62_armor = {
            "front_turret":  102,
            "front_hull": 242
        }
        t62_angle = {
            "front_turret": 5,
            "front_hull": 45
        }
       #placeholder
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t62_armor, angle_dict=t62_angle)

class T64(TrackedVehicle): #MBT Tracked placeholder
    def __init__(self, x , y, image_surface, team="A", armor_dict=None, angle_dict=None):
        t55_armor = {
            "front_turret":  99, # they gotta have this on the war thunder forums
            "front_hull": 203
        }
        t55_angle = {
            "front_turret": 5,
            "front_hull": 45
        }

        t64_material = {
            "front_armor": "Combination K",
            "front_turret": "Combination K"
        }
       #placeholder
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t55_armor, angle_dict=t55_angle, materials_dict=t64_material)
class T72_Ural(TrackedVehicle): #MBT Tracked
    def __init__(self, x , y, image_surface, team="A", armor_dict=None, angle_dict=None):
        t55_armor = {
            "front_turret":  99,
            "front_hull": 203
        }
        t55_angle = {
            "front_turret": 5,
            "front_hull": 45
        }
       #placeholder
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t55_armor, angle_dict=t55_angle)

class T80(TrackedVehicle): #MBT Tracked placeholder
    def __init__(self, x , y, image_surface, team="A", armor_dict=None, angle_dict=None):
        t55_armor = {
            "front_turret":  99,
            "front_hull": 203
        }
        t55_angle = {
            "front_turret": 5,
            "front_hull": 45
        }
       #placeholder
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t55_armor, angle_dict=t55_angle)
class Tiran5(T55): #inherit t55a
    pass #placeholder

class Magach3(TrackedVehicle): # MBT, track
    pass #placeholder



CELL_SIZE = 40 # placeholder
GRID_COLS = WIDTH // CELL_SIZE  #for now?
GRID_ROWS = 640 // CELL_SIZE    

class Cell:
    def __init__(self, gx, gy, terrain_type="open"):
        self.gx = gx
        self.gy = gy
        self.terrain_type = terrain_type
        self.move_weight = 1.0
        self.cover_val = 0.05
        self.color = (55, 68, 50)
        self.occupant = None
        self.setup_terrain(terrain_type)
# make terrain a dictionary
        #terrain = { high spot bonus means the unit inside spots better, concealment means a reduction in enemy spotting power and they can't rangefind as well, cover means hits have a chance of not daeling damage
        # "type": grass { "color" :(46, 117, 89), "cover": 0.05, "weight": 1.0, "concealment": 0.1, "spotBonus": 1, "trackDegrade": 0, "armor": 0}, 
        # "type": dry river{ color: (111, 117, 126), "cover": 0.05, "weight": 1.5, "concealment": 0.05, "spotBonus": 1, "trackDegrade": 0, "armor": 0}
        # "type": wall, color: (111, 117, 126), "cover": 0.95, "weight": 1.5, "concealment": 0.05, "spotBonus": 1,              # same color
        # "type": fence river, color: (111, 117, 126), "cover": 0.05, "weight": 1.5, "concealment": 0.05, "spotBonus": 1,},
        #}
    def setup_terrain(self, t_type): # ALL OF THESE ARE JUST PLACEHOLDERS, I WILL BE DRAWING SOME STUFF FOR THE GRIDS, ASLO GRIDS ARE WAYYY TO SMALL, MAKE THEM ~150 PIXELS AND INVISIBLE, at least 150 pixels
        self.terrain_type = t_type #todo: Walls, ditch?, big buildings? rubble and damaged roads, weather effects, sand and snow, hills? impassable mountains, land mines and stuff.
        if t_type == "road":
            self.move_weight = 0.4
            self.cover_val = 0.0
            self.color = (110, 110, 110)
        elif t_type == "open":
            self.move_weight = 1.0
            self.cover_val = 0.15
            self.color = (58, 126, 68)
        elif t_type == "rough": # something like a tank track damage???? things???
            self.move_weight = 2.0
            self.cover_val = 0.45
            self.color = (111, 117, 126)
        elif t_type == "forest": #add a speed debuff
            self.move_weight = 2.6
            self.cover_val = 0.80
            self.color = (119, 163, 122)
        elif t_type == "building":
            self.move_weight = 999.0 # cant move through, but one day we're ading building occupation
            self.cover_val = 0.95
            self.color = (105, 100, 95)

class TacticalGrid:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[Cell(x, y) for y in range(rows)] for x in range(cols)]
        self.generate_procedural_map()

    def generate_procedural_map(self):
        # Create a central road
        for x in range(self.cols):
            self.cells[x][7].setup_terrain("road")
        # Create some forest groves
        for x in range(4, 9):
            for y in range(2, 6):
                self.cells[x][y].setup_terrain("forest")
        for x in range(22, 28):
            for y in range(9, 14):
                self.cells[x][y].setup_terrain("forest")

        for x in range(12, 17):
            for y in range(10, 14):
                self.cells[x][y].setup_terrain("rough")

        buildings = [(15, 3), (16, 3), (15, 4), (16, 4)]
        for bx, by in buildings:
            self.cells[bx][by].setup_terrain("building")

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
            if neighbor.occupant is not None and (nx, ny) != (goal_gx, goal_gy) and neighbor.occupant != moving_team: #cant stack a unit
                continue

            # different weights based on what order was given
            if order_mode in ["Normal", "Quick"]:
                step_cost = neighbor.move_weight
            elif order_mode == "Fast":
                step_cost = 0.2 if neighbor.terrain_type == "road" else (neighbor.move_weight * 1.5)
            elif order_mode == "Sneak": # give a move away from enemy bonus
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

class InfantryTeam(pygame.sprite.Sprite):
  #were gonna change this one day
    def __init__(self, name, squad, team_color="blue", gx=0, gy=0):
        super().__init__()
        self.name = name
        self.squad = squad
        self.team = team_color  
        self.members = []
        self.gx = gx
        self.gy = gy
        self.pos = pygame.Vector2(gx * CELL_SIZE + 20, gy * CELL_SIZE + 20)
        self.path = []
        self.move_order = "Normal"
        self.speed = 1.8
        self.selected = False
        self.collision_radius = 14
        self.under_fire = False
        self.shoot_cooldown = 0
        self.suppression = 0.0 
        self.current_action = "Spotting"

        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def add_soldier(self, soldier: Soldier):
        self.members.append(soldier)
        self.squad.add_member(soldier)

    def total_health(self):
        return sum(m.condition for m in self.members)

    def avg_morale(self):
        if not self.members: return 0
        return sum(m.morale for m in self.members) / len(self.members)

    def apply_damage(self, caliber, projectile_type):
        damage = max(15, caliber * 0.4)
        self.suppression = min(100.0, self.suppression + 35.0) 
        for s in self.members:
            if s.condition > 0:
                s.condition = max(0, s.condition - int(damage))
                s.morale = max(0, s.morale - 12)
                break
        self.under_fire = True

    def set_order(self, order_name): 
        self.move_order = order_name
        if order_name == "Normal":
            self.speed = 1.8
        elif order_name == "Quick":
            self.speed = 3.0
        elif order_name == "Fast":
            self.speed = 3.2
        elif order_name == "Sneak":
            self.speed = 1.0
        elif order_name == "Assault":
            self.speed = 2.2
        elif order_name == "Halt":
            self.path.clear()

    def update(self, grid: TacticalGrid, all_teams, projectiles_group):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
# were gonna change this one day so that its based on markov decision making and different unit attributes like morale, training, and experience changes it slightly
        if self.suppression > 0:
            self.suppression = max(0.0, self.suppression - 0.15)
        target_enemy = None
        for other in all_teams:
            if other.team != self.team and other.total_health() > 0:
                dist = self.pos.distance_to(other.pos)
                if dist < 220:
                    target_enemy = other
                    break

        if target_enemy:
            if self.move_order == "Sneak" and self.under_fire:
                self.current_action = "Evading"
                best_cover = None
                best_val = -1
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        c = grid.get_cell(self.gx + dx, self.gy + dy)
                        if c and c.move_weight < 999.0 and c.cover_val > best_val:
                            best_val = c.cover_val
                            best_cover = c
                if best_cover and (best_cover.gx, best_cover.gy) != (self.gx, self.gy):
                    self.path = astar_pathfind(grid, self.gx, self.gy, best_cover.gx, best_cover.gy, "Sneak", self)
                self.under_fire = False

            if self.move_order == "Assault" and self.pos.distance_to(target_enemy.pos) <= 120:
                self.path.clear()
                self.current_action = "Assault Firing"
                if self.shoot_cooldown <= 0:
                    projectiles_group.add(Projectile(self.pos.x, self.pos.y, 1, target_enemy.pos, 0, 7.62, "ball", self.team))
                    self.shoot_cooldown = 40
            elif self.shoot_cooldown <= 0:
                self.current_action = "Firing"
                projectiles_group.add(Projectile(self.pos.x, self.pos.y, 1, target_enemy.pos, 0, 7.62, "ball", self.team))
                self.shoot_cooldown = 50
        elif self.path:
            self.current_action = f"Moving ({self.move_order})"
        else:
            self.current_action = "Spotting"

        if self.path:
            nxt_gx, nxt_gy = self.path[0]
            target_pos = grid.grid_to_world_center(nxt_gx, nxt_gy)
            vec = target_pos - self.pos
            dist = vec.length()
            if dist <= self.speed:
                curr_cell = grid.get_cell(self.gx, self.gy)
                if curr_cell and curr_cell.occupant == self:
                    curr_cell.occupant = None

                self.pos = target_pos
                self.gx, self.gy = nxt_gx, nxt_gy
                self.path.pop(0)

                new_cell = grid.get_cell(self.gx, self.gy)
                if new_cell:
                    new_cell.occupant = self
            else:
                self.pos += vec.normalize() * self.speed

        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def draw(self, surface):
        if self.total_health() <= 0:
            return
        if self.selected and self.path:
            pts = [self.pos] + [pygame.Vector2(gx * CELL_SIZE + 20, gy * CELL_SIZE + 20) for gx, gy in self.path]
            if len(pts) > 1:
                pygame.draw.lines(surface, (240, 240, 80), False, pts, 2)

        color = (40, 120, 240) if self.team == "blue" else (220, 50, 50)
        pygame.draw.circle(surface, color, (int(self.pos.x), int(self.pos.y)), self.collision_radius)
        if self.selected:
            pygame.draw.circle(surface, (255, 230, 70), (int(self.pos.x), int(self.pos.y)), self.collision_radius + 4, 2)

        count = sum(1 for m in self.members if m.condition > 0)
        for i in range(count):
            ox = (i - (count - 1) / 2) * 6
            pygame.draw.circle(surface, (230, 230, 230), (int(self.pos.x + ox), int(self.pos.y)), 2)


class Button:
    def __init__(self, rect, title, hotkey="", callback=None, active=False):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.hotkey = hotkey
        self.callback = callback
        self.active = active

    def draw(self, surface, font_main, font_sub):
        mpos = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mpos)
#button colors, ooh we can do like a 3d bevel effect with light and dark borders, and change the color when hovered or active oh my god we can do like a desert and a mountain and a forest and afaaaaaa one witth diffenre kolors!
        if self.active:
            base_color = (65, 80, 50)
            border_light = (180, 220, 120)
            border_dark = (35, 45, 25)
            text_color = (255, 245, 140)
        elif hovered:
            base_color = (52, 60, 54)
            border_light = (145, 155, 140)
            border_dark = (25, 30, 25)
            text_color = (255, 255, 255)
        else:
            base_color = (40, 46, 42)
            border_light = (85, 95, 85)
            border_dark = (20, 24, 20)
            text_color = (224, 255, 255)

        pygame.draw.rect(surface, base_color, self.rect)

        pygame.draw.line(surface, border_light, self.rect.topleft, self.rect.topright, 2)
        pygame.draw.line(surface, border_light, self.rect.topleft, self.rect.bottomleft, 2)
        pygame.draw.line(surface, border_dark, self.rect.bottomleft, self.rect.bottomright, 2)
        pygame.draw.line(surface, border_dark, self.rect.topright, self.rect.bottomright, 2)

        txt_surf = font_main.render(self.title, True, text_color)
        surface.blit(txt_surf, txt_surf.get_rect(center=(self.rect.centerx, self.rect.centery - (2 if self.hotkey else 0))))

        if self.hotkey:
            hk_surf = font_sub.render(f"[{self.hotkey}]", True, (160, 175, 150))
            surface.blit(hk_surf, (self.rect.right - hk_surf.get_width() - 4, self.rect.bottom - hk_surf.get_height() - 2))

    def handle_click(self, mpos):
        if self.rect.collidepoint(mpos) and self.callback:
            self.callback()
            return True
        return False

async def main():
    damage_mangr = DamageManager()
    collision_mangr = CollisionManager()
    units_group = pygame.sprite.Group() 
    projectiles_group = pygame.sprite.Group()
    buildings_group = pygame.sprite.Group()

    game_state = "START"
    tactical_grid = TacticalGrid(GRID_COLS, GRID_ROWS)

    all_teams = []
    selected_team = None

    def spawn_squad(team_side, gx, gy):
        leader = Soldier("Sgt. KIRK" if team_side == "blue" else "Sgt. KIRK", "Sergeant", "Weapon_Placeholder" if team_side == "blue" else "Weapon_Placeholder")
        squad = Squad(leader)

        team_a = InfantryTeam(f"{team_side.upper()} Team A", squad, team_side, gx, gy)
        team_a.add_soldier(leader)
        team_a.add_soldier(Soldier("Cpl. KIRK", "Corporal", "Weapon_Placeholder" if team_side == "blue" else "Weapon_Placeholder"))
        team_a.add_soldier(Soldier("Pvt. KIRK", "Private", "Weapon_Placeholder" if team_side == "blue" else "Weapon_Placeholder "))

        team_b = InfantryTeam(f"{team_side.upper()} Team B", squad, team_side, gx + 1, gy)
        team_b.add_soldier(Soldier("Cpl. KIRK", "Corporal", "Weapon_Placeholder" if team_side == "blue" else "Weapon_Placeholder"))
        team_b.add_soldier(Soldier("Pvt. KIRK", "Private", "Weapon_Placeholder" if team_side == "blue" else "Weapon_Placeholder"))

        squad.fireteams.extend([team_a, team_b])
        for t in [team_a, team_b]:
            c = tactical_grid.get_cell(t.gx, t.gy)
            if c: c.occupant = t
            units_group.add(t)
            all_teams.append(t)

    spawn_squad("blue", 2, 4)
    spawn_squad("red", 28, 4)

    def set_current_order(order_name):
        if selected_team:
            selected_team.set_order(order_name)

    def start_demo():
        nonlocal game_state
        game_state = "DEMO"

    def open_help():
        nonlocal game_state
        game_state = "HELP"

    def back_to_menu():
        nonlocal game_state
        game_state = "START"

    # Start Screen buttons
    start_btn = Button((WIDTH // 2 - 130, HEIGHT // 2 - 40, 260, 50), "Demo", "ENTER", start_demo)
    help_btn  = Button((WIDTH // 2 - 130, HEIGHT // 2 + 30, 260, 50), "guide, will have pages soon", "F1", open_help)
    back_btn  = Button((WIDTH // 2 - 100, HEIGHT - 100, 200, 45), "Quit", "ESC", back_to_menu)

    order_buttons = [
        Button((WIDTH - 365, 672, 110, 36), "MOVE", "N", lambda: set_current_order("Normal")),
        Button((WIDTH - 245, 672, 110, 36), "QUICK", "Q", lambda: set_current_order("Quick")),
        Button((WIDTH - 125, 672, 110, 36), "FAST", "F", lambda: set_current_order("Fast")),
        Button((WIDTH - 365, 715, 110, 36), "SNEAK", "S", lambda: set_current_order("Sneak")),
        Button((WIDTH - 245, 715, 110, 36), "ASSAULT", "A", lambda: set_current_order("Assault")),
        Button((WIDTH - 125, 715, 110, 36), "HALT", "H", lambda: set_current_order("Halt")),
    ]

    spawn_blue_btn = Button((375, 646, 175, 24), "+ BLUE FIRETEAM", "B", lambda: spawn_squad("blue", random.randint(1, 4), random.randint(1, 14)))
    spawn_red_btn  = Button((560, 646, 175, 24), "+ RED OPFOR", "R", lambda: spawn_squad("red", random.randint(26, 30), random.randint(1, 14)))

    font_title = pygame.font.SysFont("Jokerman ", 36) # there should be an option for the game to be all in wingdings just to fuck with people
    font_big = pygame.font.SysFont("Verdana", 14, bold=True) 
    font_normal = pygame.font.SysFont("Verdana", 13, bold=False) # im having too much fun
    font_subscript = pygame.font.SysFont("Verdana", 11)

    running = True
    while running:
        mpos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "START":
                    start_btn.handle_click(mpos)
                    help_btn.handle_click(mpos)
                elif game_state == "HELP":
                    back_btn.handle_click(mpos)
                elif game_state == "DEMO":
                    if event.button == 1:
                        clicked_ui = False
                        for btn in order_buttons + [spawn_blue_btn, spawn_red_btn]:
                            if btn.handle_click(mpos):
                                clicked_ui = True
                                break

                        if not clicked_ui and mpos[1] < 640:
                            gx, gy = tactical_grid.world_to_grid(mpos[0], mpos[1])
                            cell = tactical_grid.get_cell(gx, gy)
                            if cell and cell.occupant:
                                if selected_team:
                                    selected_team.selected = False
                                selected_team = cell.occupant
                                selected_team.selected = True
                            elif selected_team:
                                path = astar_pathfind(tactical_grid, selected_team.gx, selected_team.gy, gx, gy, selected_team.move_order, selected_team)
                                if path:
                                    selected_team.path = path

                    elif event.button == 3:
                        if selected_team:
                            selected_team.selected = False
                            selected_team = None
            #shortcuts todo: call artillery, fixed wing, rotary wing, fire, area fire, smoke, dismount, mount, take ammo.
            elif event.type == pygame.KEYDOWN and game_state == "DEMO" and selected_team:
                if event.key == pygame.K_n: set_current_order("Normal")
                elif event.key == pygame.K_q: set_current_order("Quick")
                elif event.key == pygame.K_f: set_current_order("Fast")
                elif event.key == pygame.K_s: set_current_order("Sneak")
                elif event.key == pygame.K_a: set_current_order("Assault")
                elif event.key == pygame.K_h: set_current_order("Halt")

        if game_state == "DEMO":
            collision_mangr.update(units_group, buildings_group)
            projectiles_group.update()
            for t in all_teams:
                t.update(tactical_grid, all_teams, projectiles_group)
            damage_mangr.update(projectiles_group, units_group)

        screen.fill((25, 27, 25))

        if game_state == "START":
            title = font_title.render("Halloween game that is now 5 days late", True, (230, 225, 210)) # update the days every time I edit the code 
            sub = font_big.render("I swear those black dots on kfc chicken aren't peppers", True, (165, 175, 150))
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3 - 30)))
            screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 15)))
            start_btn.draw(screen, font_big, font_subscript)
            help_btn.draw(screen, font_big, font_subscript)

        elif game_state == "HELP":
            panel = pygame.Rect(180, 60, WIDTH - 360, HEIGHT - 180)
            pygame.draw.rect(screen, (36, 42, 38), panel)
            pygame.draw.rect(screen, (75, 88, 75), panel, 2)

            help_lines = [
                ("Guide", True),
                ("Left click to select a unit.", False),
                ("Left click on the map after selecting a unit to issue a movement order.", False),
                ("Right click map to deselect a unit.", False),
                (" Hotkeys: [N] Normal, [Q] Quick, [F] Fast, [S] Sneak, [A] Assault, [H] Halt", False),
                ("", False),
                ("Movement Orders:", True),
                ("1. Move: No fatigue slightly reduced spotting straight pathing.", False),
                ("2. Quick: Faster than normal with same priorities, drains stamina.", False),
                ("3. Fast: Runs slightly faster than quick and prioritizes roads.", False),
                ("4. Sneak: Slow movement that prioritizes cover. Will hide if attacked", False),
                ("5. Assault: Incomplete? Should be gathers the squad and attacks, halts to engage but we don'thave indvidual soldiers modeled yet ", False),
                ("6. Halt: Staph!", False),
            ]
            y_offset = 85
            for line, is_header in help_lines:
                fnt = font_big if is_header else font_normal
                clr = (255, 220, 100) if is_header else (210, 220, 210)
                txt_surf = fnt.render(line, True, clr)
                screen.blit(txt_surf, (215, y_offset))
                y_offset += 30

            back_btn.draw(screen, font_big, font_subscript)

        elif game_state == "DEMO":
            tactical_grid.draw(screen)

            for t in all_teams:
                t.draw(screen)
            projectiles_group.draw(screen)
            buildings_group.draw(screen)
#UI panel area
            console_rect = pygame.Rect(0, 640, WIDTH, 160)
            pygame.draw.rect(screen, (28, 35, 31), console_rect)  
            pygame.draw.line(screen, (70, 80, 70), (0, 640), (WIDTH, 640), 2)
            panel_left = pygame.Rect(8, 646, 350, 146)
            pygame.draw.rect(screen, (24, 28, 25), panel_left)
            pygame.draw.rect(screen, (55, 65, 55), panel_left, 1)

            # unit symbol
            unit_box = pygame.Rect(18, 656, 46, 34)
            pygame.draw.rect(screen, (40, 50, 42), unit_box)
            pygame.draw.rect(screen, (130, 150, 130), unit_box, 1)
            pygame.draw.line(screen, (130, 150, 130), unit_box.topleft, unit_box.bottomright, 1)
            pygame.draw.line(screen, (130, 150, 130), unit_box.bottomleft, unit_box.topright, 1)
            pygame.draw.circle(screen, (200, 220, 200), (41, 673), 3)

            if selected_team:
                team_clr = (140, 190, 255) if selected_team.team == "blue" else (255, 140, 140)
                name_lbl = font_big.render(selected_team.name, True, team_clr)
                lead_lbl = font_subscript.render(f"HQ: {selected_team.squad.leader.name}", True, (180, 190, 180))
                c2_lbl   = font_subscript.render("C2 LINK: VOICE / SIGHT (100%)", True, (120, 220, 120)) # radios soon(TM)
                screen.blit(name_lbl, (74, 656))
                screen.blit(lead_lbl, (74, 674))
                screen.blit(c2_lbl, (74, 690))

                supp_txt = font_subscript.render("SUPPRESSION", True, (160, 170, 160))
                screen.blit(supp_txt, (18, 712))
                bar_bg = pygame.Rect(18, 727, 180, 12)
                pygame.draw.rect(screen, (15, 18, 15), bar_bg)
                pygame.draw.rect(screen, (60, 70, 60), bar_bg, 1)
                supp_pct = min(1.0, selected_team.suppression / 100.0)
                if supp_pct > 0:
                    fill_clr = (220, 70, 50) if supp_pct > 0.6 else (230, 180, 40)
                    pygame.draw.rect(screen, fill_clr, (19, 728, int(178 * supp_pct), 10))

                # Morale & State
                morale_val = selected_team.avg_morale()
                state_str = "OK" if morale_val > 70 else ("CAUTIOUS" if morale_val > 40 else "SHAKEN")
                state_lbl = font_big.render(f"MORALE: {state_str}", True, (210, 215, 180))
                action_lbl = font_subscript.render(f"ACTION: {selected_team.current_action.upper()}", True, (180, 220, 140))
                screen.blit(state_lbl, (210, 712))
                screen.blit(action_lbl, (18, 748))
            else:
                lbl_none = font_normal.render("NO UNIT SELECTED", True, (120, 130, 120))
                screen.blit(lbl_none, (74, 665))
                sub_none = font_subscript.render("Left-click unit to inspect and command", True, (90, 100, 90))
                screen.blit(sub_none, (18, 715))
# will add running out of ammo and reloading later
            panel_center = pygame.Rect(366, 646, 530, 146)
            pygame.draw.rect(screen, (24, 28, 25), panel_center)
            pygame.draw.rect(screen, (55, 65, 55), panel_center, 1)

            spawn_blue_btn.draw(screen, font_normal, font_subscript)
            spawn_red_btn.draw(screen, font_normal, font_subscript)

            if selected_team:
                roster_hdr = font_big.render("Info", True, (165, 175, 150))
                screen.blit(roster_hdr, (376, 678))
                y_soldier = 700
                for s in selected_team.members:
                    cond_clr = (140, 220, 140) if s.condition > 150 else ((240, 180, 50) if s.condition > 50 else (220, 60, 60))
                    cond_txt = "FIT" if s.condition > 150 else ("Shot" if s.condition > 50 else "KIRKED!")
                    s_str = f"{s.rank} {s.name}  --  {s.weapon}"
                    txt_s = font_subscript.render(s_str, True, (210, 215, 210))
                    txt_c = font_subscript.render(f"[{cond_txt}]", True, cond_clr)
                    screen.blit(txt_s, (376, y_soldier))
                    screen.blit(txt_c, (620, y_soldier))
                    y_soldier += 18

                ammo_box = pygame.Rect(720, 678, 165, 78)
                pygame.draw.rect(screen, (18, 22, 19), ammo_box)
                pygame.draw.rect(screen, (50, 60, 50), ammo_box, 1)
                screen.blit(font_big.render("AMMUNITION", True, (180, 190, 170)), (730, 684))
                screen.blit(font_subscript.render("boolets", True, (200, 205, 195)), (730, 704))
                screen.blit(font_subscript.render("pasta", True, (200, 205, 195)), (730, 720))
                screen.blit(font_subscript.render("Smoke", True, (200, 205, 195)), (730, 736))

            panel_right = pygame.Rect(904, 646, 368, 146)
            pygame.draw.rect(screen, (24, 28, 25), panel_right)
            pygame.draw.rect(screen, (55, 65, 55), panel_right, 1)

            tab_mov = pygame.Rect(910, 648, 110, 20)
            pygame.draw.rect(screen, (55, 68, 55), tab_mov)
            pygame.draw.rect(screen, (100, 120, 100), tab_mov, 1)
            screen.blit(font_big.render("MOVEMENT", True, (255, 250, 180)), (922, 650))

            tab_com = pygame.Rect(1025, 648, 110, 20)
            pygame.draw.rect(screen, (32, 38, 33), tab_com)
            screen.blit(font_subscript.render("COMBAT", True, (130, 140, 130)), (1055, 651))

            tab_spc = pygame.Rect(1140, 648, 110, 20)
            pygame.draw.rect(screen, (32, 38, 33), tab_spc)
            screen.blit(font_subscript.render("SPECIAL", True, (130, 140, 130)), (1170, 651))

            for btn in order_buttons:
                btn_order_map = {
                    "MOVE": "Normal", "QUICK": "Quick", "FAST": "Fast",
                    "SLOW/SNEAK": "Sneak", "ASSAULT": "Assault", "HALT": "Halt"
                }
                btn.active = bool(selected_team and selected_team.move_order == btn_order_map.get(btn.title))
                btn.draw(screen, font_normal, font_subscript)

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

asyncio.run(main())

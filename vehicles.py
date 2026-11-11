# vehicles.py
import pygame

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
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, angle=0, team="blue", req_points=80, rarity_points=15, is_full_unit=False):
        super().__init__()
        self.angle = angle
        self.team = team
        self.original_image = image_surface
        self.image = self.original_image.copy() if image_surface else pygame.Surface((32, 20), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration_magnitude = 0.0
        self.req_points = req_points * (3 if is_full_unit else 1)
        self.rarity_points = rarity_points * (2 if is_full_unit else 1)
        self.is_full_unit = is_full_unit

    def move(self):
        pass

class WheeledVehicle(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, req_points=70, rarity_points=10, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, req_points=req_points, rarity_points=rarity_points, is_full_unit=is_full_unit)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}

class TrackedVehicle(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, req_points=150, rarity_points=30, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, req_points=req_points, rarity_points=rarity_points, is_full_unit=is_full_unit)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}

class HalfTracked(Vehicle):
    def __init__(self, x, y, length, height, max_speed, acceleration, image_surface, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, req_points=80, rarity_points=15, is_full_unit=False):
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, req_points=req_points, rarity_points=rarity_points, is_full_unit=is_full_unit)
        self.armor = armor_dict if armor_dict else {}
        self.surface_angles = angle_dict if angle_dict else {}
        self.armor_materials = materials_dict if materials_dict else {}

class ZIL131(WheeledVehicle):
    def __init__(self, x, y, image_surface=None, length=7.0, height=2.4, max_speed=80, acceleration=1.2, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        truck_armor = {'front_window': 30, 'front_hull': 5, 'side_hull': 3, 'rear_hull': 2, 'roof': 0}
        truck_angle = {'window_angle': 5, 'front_angle': 0, 'side_angle': 0, 'rear_angle': 0, 'roof_angle': 0}
        truck_material = {'glass', 'steel'}
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=truck_armor, angle_dict=truck_angle, materials_dict=truck_material, req_points=40, rarity_points=5, is_full_unit=is_full_unit)

class BRDM(WheeledVehicle):
    def __init__(self, x, y, image_surface=None, length=5.75, height=2.31, max_speed=100, acceleration=1.8, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        brdm_armor = {'nose_armor': 14, 'front_turret': 10, 'front_hull': 14, 'side_armor': 7, 'roof_armor': 7}
        brdm_angle = {'nose_armor': 40, 'font_lower_angle': 35, 'front_upper_angle': 30, 'side_angle': 45, 'rear_angle': 0}
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=brdm_armor, angle_dict=brdm_angle, req_points=75, rarity_points=15, is_full_unit=is_full_unit)

class Zachlam(HalfTracked):
    def __init__(self, x, y, image_surface=None, length=6.0, height=2.2, max_speed=72, acceleration=1.4, azimuth=0, team="blue", armor_dict=None, angle_dict=None, materials_dict=None, is_full_unit=False):
        zachlam_armor = {'nose_armor': 14, 'front_turret': 10, 'front_hull': 14, 'side_armor': 7, 'roof_armor': 7}
        zachlam_angle = {'nose_armor': 40, 'front_lower_angle': 35, 'front_upper_angle': 30, 'side_angle': 45, 'rear_angle': 0}
        super().__init__(x, y, length, height, max_speed, acceleration, image_surface, azimuth, team, armor_dict=zachlam_armor, angle_dict=zachlam_angle, req_points=65, rarity_points=12, is_full_unit=is_full_unit)

class T55(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t55_armor = {"front_turret": 99, "front_hull": 203}
        t55_angle = {"front_turret": 5, "front_hull": 45}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t55_armor, angle_dict=t55_angle, req_points=160, rarity_points=25, is_full_unit=is_full_unit)

class T62(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t62_armor = {"front_turret": 99, "front_hull": 203}
        t62_angle = {"front_turret": 5, "front_hull": 45}
        t62_material = {"front_turret": "HHA"}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t62_armor, angle_dict=t62_angle, materials_dict=t62_material, req_points=190, rarity_points=35, is_full_unit=is_full_unit)

class T62_1972(T62):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t62_armor = {"front_turret": 102, "front_hull": 242}
        t62_angle = {"front_turret": 5, "front_hull": 45}
        TrackedVehicle.__init__(self, x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t62_armor, angle_dict=t62_angle, req_points=190, rarity_points=35, is_full_unit=is_full_unit)

class T64(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t64_armor = {"front_turret": 99, "front_hull": 203}
        t64_angle = {"front_turret": 5, "front_hull": 45}
        t64_material = {"front_armor": "Combination K", "front_turret": "Combination K"}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t64_armor, angle_dict=t64_angle, materials_dict=t64_material, req_points=240, rarity_points=60, is_full_unit=is_full_unit)

class T72_Ural(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t72_armor = {"front_turret": 99, "front_hull": 203}
        t72_angle = {"front_turret": 5, "front_hull": 45}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t72_armor, angle_dict=t72_angle, req_points=250, rarity_points=65, is_full_unit=is_full_unit)

class T80(TrackedVehicle):
    def __init__(self, x, y, image_surface=None, team="A", armor_dict=None, angle_dict=None, is_full_unit=False):
        t80_armor = {"front_turret": 99, "front_hull": 203}
        t80_angle = {"front_turret": 5, "front_hull": 45}
        super().__init__(x, y, 9.0, 2.4, 50, 1.5, image_surface, team=team, armor_dict=t80_armor, angle_dict=t80_angle, req_points=320, rarity_points=90, is_full_unit=is_full_unit)

class Tiran5(T55):
    pass

class Magach3(TrackedVehicle):
    pass
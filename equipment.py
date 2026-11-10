#equipment.py all the stuff that doesn't actually have a sprite or any physical anything but is still important tot he game 
 
class WeaponItem:
    def __init__(self, name, caliber=7.62, req_points=5, rarity_points=0):
        self.name = name
        self.caliber = caliber
        self.req_points = req_points
        self.rarity_points = rarity_points

class Gun(WeaponItem):
    def __init__(self, name="gungun", caliber=7.62, gun_type="Rifle", req_points=8, rarity_points=0):
        super().__init__(name, caliber, req_points, rarity_points)
        self.gun_type = gun_type

class Grenade:
    def __init__(self, name="Placeholder", count=2, req_points=4, rarity_points=0):
        self.name = name
        self.count = count
        self.req_points = req_points
        self.rarity_points = rarity_points

class Mortar:
    def __init__(self, name="Placeholder", caliber=82, on_map=True, req_points=45, rarity_points=10):
        self.name = name
        self.caliber = caliber
        self.on_map = on_map
        self.req_points = req_points
        self.rarity_points = rarity_points

class Radio:
    def __init__(self, name="Placeholder", signal_strength=100, req_points=15, rarity_points=5):
        self.name = name
        self.signal_strength = signal_strength
        self.req_points = req_points
        self.rarity_points = rarity_points

class ArtilleryPiece:
    def __init__(self, name="Placeholder", caliber=122, piece_type="howitzer", on_map=False, req_points=120, rarity_points=25, is_full_unit=False):
        self.name = name
        self.caliber = caliber
        self.piece_type = piece_type  # 'howitzer', 'recoilless', 'at_gun', 'mrls'
        # Howitzers are strictly off map per doctrine
        if self.piece_type == "howitzer":
            self.on_map = False
        else:
            self.on_map = on_map
        self.is_full_unit = is_full_unit
        self.req_points = req_points * (3 if is_full_unit else 1)
        self.rarity_points = rarity_points * (2 if is_full_unit else 1)

class AircraftLoadoutItem:
    def __init__(self, name="Placeholder", item_type="none", req_points=20, rarity_points=5):
        self.name = name
        self.item_type = item_type  # 'bomb', 'rocket', 'cannon'
        self.req_points = req_points
        self.rarity_points = rarity_points

class Plane:
    def __init__(self, name="Placeholder", base_req_points=180, base_rarity=40, loadout=None):
        self.name = name
        self.base_req_points = base_req_points
        self.base_rarity = base_rarity
        self.loadout = loadout if loadout is not None else []

    @property
    def total_req_points(self):
        return self.base_req_points + sum(item.req_points for item in self.loadout)

    @property
    def total_rarity_points(self):
        return self.base_rarity + sum(item.rarity_points for item in self.loadout)
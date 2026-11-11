# equipment.py - Armament, communications, ordnance, and loadout definitions

class WeaponItem:
    def __init__(self, name, caliber=7.62, req_points=5, rarity_points=0, effective_range=300):
        self.name = name
        self.caliber = caliber
        self.req_points = req_points
        self.rarity_points = rarity_points
        self.effective_range = effective_range

class Gun(WeaponItem):
    def __init__(self, name="AK-47", caliber=7.62, gun_type="Rifle", req_points=8, rarity_points=0, 
                 effective_range=350, fire_rate=45, muzzle_velocity=715, suppression_factor=1.0):
        super().__init__(name, caliber, req_points, rarity_points, effective_range)
        self.gun_type = gun_type  # 'Rifle', 'MachineGun', 'Sniper', 'Pistol', 'SMG'
        self.fire_rate = fire_rate  # Cooldown ticks between bursts
        self.muzzle_velocity = muzzle_velocity
        self.suppression_factor = suppression_factor

        # Standard preset adjustments
        if gun_type == "MachineGun":
            self.suppression_factor = 2.4
            self.fire_rate = 22
            self.effective_range = 550
        elif gun_type == "Sniper":
            self.suppression_factor = 1.8
            self.fire_rate = 75
            self.effective_range = 700

class Grenade:
    def __init__(self, name="F1 Fragmentation", count=2, req_points=4, rarity_points=0, blast_radius=45, damage=110):
        self.name = name
        self.count = count
        self.req_points = req_points
        self.rarity_points = rarity_points
        self.blast_radius = blast_radius
        self.damage = damage

class AntiTankLauncher:
    def __init__(self, name="RPG-7", caliber=85, req_points=24, rarity_points=5, armor_penetration=300, min_range=40, max_range=300):
        self.name = name
        self.caliber = caliber
        self.req_points = req_points
        self.rarity_points = rarity_points
        self.armor_penetration = armor_penetration
        self.min_range = min_range
        self.max_range = max_range

class Mortar:
    def __init__(self, name="82-BM-37 82mm", caliber=82, on_map=True, req_points=50, rarity_points=10, 
                 min_range=150, max_range=1200, burst_shells=4):
        self.name = name
        self.caliber = caliber
        self.on_map = on_map
        self.req_points = req_points
        self.rarity_points = rarity_points
        self.min_range = min_range
        self.max_range = max_range
        self.burst_shells = burst_shells

class Radio:
    def __init__(self, name="R-105M Tactical VHF", signal_strength=100, req_points=15, rarity_points=5, voice_c2_bonus=20):
        self.name = name
        self.signal_strength = signal_strength
        self.req_points = req_points
        self.rarity_points = rarity_points
        self.voice_c2_bonus = voice_c2_bonus

class ArtilleryPiece:
    def __init__(self, name="D-30 122mm Howitzer", caliber=122, piece_type="howitzer", on_map=False, 
                 req_points=120, rarity_points=25, is_full_unit=False):
        self.name = name
        self.caliber = caliber
        self.piece_type = piece_type  # 'howitzer', 'recoilless', 'at_gun', 'mrls'
        # Heavy howitzers are placed off-map by doctrine
        self.on_map = False if piece_type == "howitzer" else on_map
        self.is_full_unit = is_full_unit
        self.req_points = req_points * (3 if is_full_unit else 1)
        self.rarity_points = rarity_points * (2 if is_full_unit else 1)

class AircraftLoadoutItem:
    def __init__(self, name="FAB-250 High Explosive", item_type="bomb", req_points=25, rarity_points=5, yield_weight=250):
        self.name = name
        self.item_type = item_type  # 'bomb', 'rocket', 'cannon', 'cluster'
        self.req_points = req_points
        self.rarity_points = rarity_points
        self.yield_weight = yield_weight

class Plane:
    def __init__(self, name="Su-25 Frogfoot", base_req_points=220, base_rarity=50, loadout=None):
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
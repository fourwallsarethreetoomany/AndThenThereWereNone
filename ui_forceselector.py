# ui/force_selector.py
from vehicles import T55, T62_1972, T64, T72_Ural, BRDM, ZIL131, Zachlam

class ForceSelector:
    def __init__(self):
        self.active_team = "Team A"
        self.budget_req = 1000
        self.budget_rar = 250

        self.nations = ["USSR", "USA", "China", "GDR", "Israel", "United Arab Republic"]
        self.selected_nation = "USSR"
        self.categories = ["Formations", "Vehicles", "Aircraft", "Artillery", "Fortification"]
        self.selected_category = "Formations"

        self.purchased_units = []
        self.catalog = self.build_catalog()

    def build_catalog(self):
        return {
            "Formations": [
                {"name": "Recon Company", "type": "formation", "req": 210, "rar": 25, "desc": "BRDM-2s + Scout Squads", "subordinates": ["2x Scout Teams", "1x BRDM-2"]},
                {"name": "AT Missile Company", "type": "formation", "req": 280, "rar": 45, "desc": "Malyutka ATGM Teams", "subordinates": ["3x ATGM Teams", "1x BTR"]},
                {"name": "AD Missile Company", "type": "formation", "req": 260, "rar": 50, "desc": "Strela-2 Air Defense Teams", "subordinates": ["3x MANPADS Teams"]},
                {"name": "MR Battalion Coy (BTR)", "type": "formation", "req": 420, "rar": 60, "desc": "Motor Rifle Coy with BTRs", "subordinates": ["3x MR Platoons", "HQ BTR"]},
                {"name": "MR Battalion Coy (BMP)", "type": "formation", "req": 560, "rar": 90, "desc": "Heavy Motor Rifle Coy with BMP-1s", "subordinates": ["3x BMP Platoons", "HQ BMP"]},
                {"name": "MR Platoon (BTR)", "type": "formation", "req": 140, "rar": 20, "desc": "1 Rifle Platoon + Transport", "subordinates": ["3x Fireteams", "1x Transport"]},
            ],
            "Vehicles": [
                {"name": "T-55A MBT (Indiv)", "type": "vehicle", "req": 160, "rar": 25, "is_full": False, "cls": T55},
                {"name": "T-55A Platoon (Full Unit)", "type": "vehicle", "req": 480, "rar": 50, "is_full": True, "cls": T55},
                {"name": "T-62 Model 1972", "type": "vehicle", "req": 190, "rar": 35, "is_full": False, "cls": T62_1972},
                {"name": "T-64A MBT", "type": "vehicle", "req": 240, "rar": 60, "is_full": False, "cls": T64},
                {"name": "T-72 Ural MBT", "type": "vehicle", "req": 250, "rar": 65, "is_full": False, "cls": T72_Ural},
                {"name": "BRDM-2 Scout", "type": "vehicle", "req": 75, "rar": 15, "is_full": False, "cls": BRDM},
                {"name": "ZIL-131 Transport Truck", "type": "vehicle", "req": 40, "rar": 5, "is_full": False, "cls": ZIL131},
                {"name": "Zachlam Half-track", "type": "vehicle", "req": 65, "rar": 12, "is_full": False, "cls": Zachlam},
            ],
            "Aircraft": [
                {"name": "Su-25 [FAB-250 x4]", "type": "aircraft", "req": 260, "rar": 55, "loadout": ["FAB-250", "30mm Cannon"]},
                {"name": "Su-25 [FAB-500 x2]", "type": "aircraft", "req": 290, "rar": 65, "loadout": ["FAB-500", "30mm Cannon"]},
                {"name": "MiG-21 [S-24 Rockets]", "type": "aircraft", "req": 220, "rar": 40, "loadout": ["S-24 Rockets", "23mm Cannon"]},
                {"name": "F-4 Phantom [MK-82 x6]", "type": "aircraft", "req": 310, "rar": 70, "loadout": ["MK-82", "20mm Vulcan"]},
                {"name": "Mi-24 Hind Gunship", "type": "aircraft", "req": 240, "rar": 50, "loadout": ["ATGM Spiral", "57mm Rockets"]},
            ],
            "Artillery": [
                {"name": "D-30 122mm Btry (Off-Map)", "type": "artillery", "req": 180, "rar": 30, "on_map": False, "is_full": True},
                {"name": "D-20 152mm Howitzer (Off-Map)", "type": "artillery", "req": 240, "rar": 45, "on_map": False, "is_full": True},
                {"name": "T-12 100mm AT Gun (On-Map)", "type": "artillery", "req": 90, "rar": 15, "on_map": True, "is_full": False},
                {"name": "T-12 AT Battery (Off-Map)", "type": "artillery", "req": 190, "rar": 35, "on_map": False, "is_full": True},
                {"name": "SPG-9 Recoilless (On-Map)", "type": "artillery", "req": 50, "rar": 10, "on_map": True, "is_full": False},
                {"name": "BM-21 Grad MRLS (On-Map)", "type": "artillery", "req": 210, "rar": 50, "on_map": True, "is_full": False},
                {"name": "BM-21 Grad Btry (Off-Map)", "type": "artillery", "req": 340, "rar": 80, "on_map": False, "is_full": True},
            ],
            "Fortification": [
                {"name": "Normal Trench Line", "type": "fortification", "req": 40, "rar": 5},
                {"name": "Underground Bunker", "type": "fortification", "req": 95, "rar": 20},
                {"name": "Dragon Teeth / AT Obstacle", "type": "fortification", "req": 30, "rar": 0},
            ]
        }

    @property
    def spent_req(self):
        return sum(u["req"] for u in self.purchased_units)

    @property
    def spent_rar(self):
        return sum(u["rar"] for u in self.purchased_units)

    @property
    def remain_req(self):
        return self.budget_req - self.spent_req

    @property
    def remain_rar(self):
        return self.budget_rar - self.spent_rar

    def add_item(self, item):
        if self.remain_req >= item["req"] and self.remain_rar >= item["rar"]:
            self.purchased_units.append(item)

    def remove_item(self, index):
        if 0 <= index < len(self.purchased_units):
            self.purchased_units.pop(index)
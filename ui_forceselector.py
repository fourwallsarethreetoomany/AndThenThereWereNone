# ui/force_selector.py - OOB Force Builder with Cold War & Central Asian theater equipment
from vehicles import T55, T62_1972, T64, T72_Ural, BRDM, ZIL131, Zachlam

class ForceSelector:
    def __init__(self):
        self.active_team = "Team A"
        self.budget_req = 1200
        self.budget_rar = 300

        self.nations = [
            "USSR 40th Army",
            "DRA Gov Forces",
            "US Central Command",
            "PLA Western Command",
            "GDR NVA Detachment",
            "Mujahideen / Militia"
        ]
        self.selected_nation = "USSR 40th Army"
        self.categories = ["Formations", "Vehicles", "Aircraft", "Artillery", "Fortification"]
        self.selected_category = "Formations"

        self.purchased_units = []
        self.catalog = self.build_catalog()

    def build_catalog(self):
        return {
            "Formations": [
                {
                    "name": "Mountain Recon Platoon",
                    "type": "formation",
                    "req": 190,
                    "rar": 20,
                    "desc": "BRDM-2 + 2x Mountain Scout Fireteams",
                    "subordinates": ["2x Mountain Scout Teams", "1x BRDM-2"]
                },
                {
                    "name": "Motor Rifle Platoon (BTR)",
                    "type": "formation",
                    "req": 260,
                    "rar": 35,
                    "desc": "Full Platoon with 3x Rifle Squads & BTR Support",
                    "subordinates": ["3x Rifle Teams", "1x BTR-60PB"]
                },
                {
                    "name": "Air Assault Platoon (VDV)",
                    "type": "formation",
                    "req": 340,
                    "rar": 60,
                    "desc": "Elite Paratrooper Squads with PKM & RPG-7V",
                    "subordinates": ["3x Elite VDV Teams", "1x BMD-1"]
                },
                {
                    "name": "Heavy ATGM Missile Section",
                    "type": "formation",
                    "req": 240,
                    "rar": 45,
                    "desc": "9M14 Malyutka / Fagot Guided Anti-Tank Crew",
                    "subordinates": ["2x ATGM Teams", "1x Transport Truck"]
                },
                {
                    "name": "Forward Air Controller & HQ",
                    "type": "formation",
                    "req": 150,
                    "rar": 30,
                    "desc": "Radio-equipped HQ Unit with Long-Range VHF",
                    "subordinates": ["1x HQ Fireteam", "1x Radio Jeep"]
                }
            ],
            "Vehicles": [
                {"name": "T-55A MBT (Main Battle Tank)", "type": "vehicle", "req": 180, "rar": 25, "is_full": False, "cls": T55},
                {"name": "T-55A Tank Platoon (3x Tanks)", "type": "vehicle", "req": 520, "rar": 55, "is_full": True, "cls": T55},
                {"name": "T-62 Model 1972 (115mm Smoothbore)", "type": "vehicle", "req": 220, "rar": 40, "is_full": False, "cls": T62_1972},
                {"name": "T-64A MBT (Composite Armor)", "type": "vehicle", "req": 290, "rar": 70, "is_full": False, "cls": T64},
                {"name": "T-72 Ural (125mm Autoloader)", "type": "vehicle", "req": 310, "rar": 75, "is_full": False, "cls": T72_Ural},
                {"name": "BRDM-2 Amphibious Scout Car", "type": "vehicle", "req": 80, "rar": 15, "is_full": False, "cls": BRDM},
                {"name": "ZIL-131 6x6 Heavy Transport", "type": "vehicle", "req": 45, "rar": 5, "is_full": False, "cls": ZIL131},
                {"name": "Zachlam Armored Personnel Carrier", "type": "vehicle", "req": 70, "rar": 10, "is_full": False, "cls": Zachlam},
            ],
            "Aircraft": [
                {"name": "Su-25 Frogfoot [FAB-250 x4]", "type": "aircraft", "req": 270, "rar": 60, "loadout": ["FAB-250", "30mm GSh-30-2"]},
                {"name": "Su-25 Frogfoot [FAB-500 x2]", "type": "aircraft", "req": 300, "rar": 70, "loadout": ["FAB-500", "30mm GSh-30-2"]},
                {"name": "MiG-21Bis [S-24 240mm Rockets]", "type": "aircraft", "req": 230, "rar": 45, "loadout": ["S-24 Heavy Rockets", "23mm Cannon"]},
                {"name": "Mi-24V Hind Gunship", "type": "aircraft", "req": 280, "rar": 65, "loadout": ["9M114 Shturm", "80mm S-8 Rockets"]},
                {"name": "F-4E Phantom II [MK-82 x6]", "type": "aircraft", "req": 320, "rar": 75, "loadout": ["MK-82", "20mm M61 Vulcan"]},
            ],
            "Artillery": [
                {"name": "82mm BM-37 Mortar Crew (On-Map)", "type": "artillery", "req": 65, "rar": 10, "on_map": True, "is_full": False},
                {"name": "120mm Heavy Mortar Battery (Off-Map)", "type": "artillery", "req": 150, "rar": 25, "on_map": False, "is_full": True},
                {"name": "D-30 122mm Battery (Off-Map Salvo)", "type": "artillery", "req": 210, "rar": 40, "on_map": False, "is_full": True},
                {"name": "D-20 152mm Gun-Howitzer (Off-Map)", "type": "artillery", "req": 270, "rar": 55, "on_map": False, "is_full": True},
                {"name": "SPG-9 73mm Recoilless Gun (On-Map)", "type": "artillery", "req": 55, "rar": 10, "on_map": True, "is_full": False},
                {"name": "BM-21 Grad MRLS Rocket Battery", "type": "artillery", "req": 360, "rar": 85, "on_map": False, "is_full": True},
            ],
            "Fortification": [
                {"name": "Reinforced Adobe Wall / Sandbags", "type": "fortification", "req": 35, "rar": 5},
                {"name": "Mountain Stone Sangar Bunker", "type": "fortification", "req": 80, "rar": 15},
                {"name": "Anti-Vehicle Dragon Teeth / Rocks", "type": "fortification", "req": 30, "rar": 0},
                {"name": "Deep Communications Trench", "type": "fortification", "req": 50, "rar": 10},
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
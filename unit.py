# units file: all the units that appear ingame defines points and stats as well as their behavior 
import pygame 
from setup import CELL_SIZE
from combat import Projectile
from equipment import Gun
from grid import TacticalGrid, astar_pathfind


class Soldier:
    def __init__(self, name, rank, weapon="weapon", gun_obj=None, grenades_obj=None, radio_obj=None): # [MODIFIED] added equipment objects
        self.name = name
        self.rank = rank
        self.weapon = weapon 
        self.condition = 200        # health, 100 to incap, 0 mean dies. incaps can be stabalized with buddy aid, above 150 can be healed up and returned with a permament morale debuff for the match. Score calculated partially based on death and injury.
        self.morale = 100           # use transition matrix to determine probability that they will go from normal to shaken to suppressed to cowering or panicked
        self.is_pinned = False
        self.assigned_squad = None
        self.gun = gun_obj if gun_obj else Gun("gungun" if "Rifle" in weapon else weapon)
        self.grenades = grenades_obj
        self.radio = radio_obj

    def calculate_cost(self):
        base_req = 10
        base_rar = 0
        if self.gun:
            base_req += self.gun.req_points
            base_rar += self.gun.rarity_points
        if self.grenades:
            base_req += self.grenades.req_points
            base_rar += self.grenades.rarity_points
        if self.radio:
            base_req += self.radio.req_points
            base_rar += self.radio.rarity_points
        return base_req, base_rar

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

    def calculate_points(self):
        total_req = 0
        total_rar = 0
        for m in self.members:
            r, rar = m.calculate_cost()
            total_req += r
            total_rar += rar
        return total_req, total_rar


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
        self.mounted = False # [ADDED] mount/dismount state
        self.assigned_vehicle = None # [ADDED] assigned transport

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

    def calculate_points(self): # [ADDED] Requisition and rarity points sum
        r, rar = 0, 0
        for m in self.members:
            cr, crar = m.calculate_cost()
            r += cr
            rar += crar
        if self.assigned_vehicle:
            r += self.assigned_vehicle.req_points
            rar += self.assigned_vehicle.rarity_points
        return r, rar

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
        elif order_name == "Mount": # [ADDED] Handle mount
            self.mounted = True
            self.current_action = "Mounted"
        elif order_name == "Dismount": # [ADDED] Handle dismount
            self.mounted = False
            self.current_action = "Dismounted"

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
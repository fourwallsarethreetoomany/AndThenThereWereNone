import random
import pygame
import asyncio

from config import WIDTH, HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS
from combat import DamageManager, CollisionManager
from equipment import Gun, Grenade, Radio
from vehicles import Vehicle
from units import Soldier, Squad, InfantryTeam
from grid import TacticalGrid, astar_pathfind
from ui.button import Button
from ui.force_selector import ForceSelector

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

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
    force_selector = ForceSelector()
    current_ui_tab = "MOVEMENT"

    def spawn_squad(team_side, gx, gy):
        ak_gun = Gun("AK-47", 7.62, "Rifle", 8, 0)
        rpd_gun = Gun("RPD MG", 7.62, "MachineGun", 16, 4)
        f1_grenades = Grenade("F1", 2, 4, 0)
        squad_radio = Radio("R-105M", 100, 15, 5)

        leader = Soldier("Sgt. KIRK", "Sergeant", "AK-47", ak_gun, f1_grenades, squad_radio)
        squad = Squad(leader)

        team_a = InfantryTeam(f"{team_side.upper()} Team A", squad, team_side, gx, gy)
        team_a.add_soldier(leader)
        team_a.add_soldier(Soldier("Cpl. KIRK", "Corporal", "RPD MG", rpd_gun, f1_grenades))
        team_a.add_soldier(Soldier("Pvt. KIRK", "Private", "AK-47", ak_gun, f1_grenades))

        team_b = InfantryTeam(f"{team_side.upper()} Team B", squad, team_side, gx + 1, gy)
        team_b.add_soldier(Soldier("Cpl. KIRK", "Corporal", "AK-47", ak_gun, f1_grenades))
        team_b.add_soldier(Soldier("Pvt. KIRK", "Private", "AK-47", ak_gun, f1_grenades))

        squad.fireteams.extend([team_a, team_b])
        for t in [team_a, team_b]:
            c = tactical_grid.get_cell(t.gx, t.gy)
            if c:
                c.occupant = t
            units_group.add(t)
            all_teams.append(t)

    def deploy_selected_forces():
        nonlocal game_state
        if not force_selector.purchased_units:
            spawn_squad("blue", 2, 4)
            spawn_squad("red", 28, 4)
            game_state = "DEMO"
            return

        all_teams.clear()
        units_group.empty()

        spawn_x = 2
        spawn_y = 2

        for item in force_selector.purchased_units:
            u_type = item.get("type")

            if u_type == "formation":
                spawn_squad("blue", spawn_x, spawn_y)
                spawn_y = (spawn_y + 3) % 13 + 1
                if spawn_y <= 3:
                    spawn_x += 3

            elif u_type == "vehicle":
                cls = item.get("cls", Vehicle)
                count = 3 if item.get("is_full", False) else 1
                for _ in range(count):
                    w_pos = tactical_grid.grid_to_world_center(spawn_x, spawn_y)
                    veh_sprite = cls(w_pos.x, w_pos.y, team="blue")
                    units_group.add(veh_sprite)
                    dummy_squad = Squad(Soldier("Crew Commander", "Sergeant", "Pistol"))
                    veh_team = InfantryTeam(item["name"], dummy_squad, "blue", spawn_x, spawn_y)
                    veh_team.assigned_vehicle = veh_sprite
                    c = tactical_grid.get_cell(spawn_x, spawn_y)
                    if c:
                        c.occupant = veh_team
                    all_teams.append(veh_team)

                    spawn_y = (spawn_y + 2) % 13 + 1
                    if spawn_y <= 2:
                        spawn_x += 2

            elif u_type == "artillery":
                if item.get("on_map", False):
                    squad = Squad(Soldier("Battery Commander", "Lieutenant", "Pistol"))
                    arty_team = InfantryTeam(item["name"], squad, "blue", spawn_x, spawn_y)
                    c = tactical_grid.get_cell(spawn_x, spawn_y)
                    if c:
                        c.occupant = arty_team
                    units_group.add(arty_team)
                    all_teams.append(arty_team)
                    spawn_y = (spawn_y + 2) % 13 + 1

        spawn_squad("red", 28, 4)
        spawn_squad("red", 27, 8)
        spawn_squad("red", 29, 11)

        game_state = "DEMO"

    def set_current_order(order_name):
        if selected_team:
            selected_team.set_order(order_name)

    def start_demo():
        nonlocal game_state
        game_state = "FORCE_SELECTOR"

    def open_force_selector():
        nonlocal game_state
        game_state = "FORCE_SELECTOR"

    def open_help():
        nonlocal game_state
        game_state = "HELP"

    def back_to_menu():
        nonlocal game_state
        game_state = "START"

    start_btn = Button((WIDTH // 2 - 130, HEIGHT // 2 - 60, 260, 45), "Demo", "ENTER", start_demo)
    forces_btn = Button((WIDTH // 2 - 130, HEIGHT // 2 - 5, 260, 45), "Force Selector", "F2", open_force_selector)
    help_btn  = Button((WIDTH // 2 - 130, HEIGHT // 2 + 50, 260, 45), "guide, will have pages soon", "F1", open_help)
    back_btn  = Button((WIDTH // 2 - 100, HEIGHT - 100, 200, 45), "Quit", "ESC", back_to_menu)

    movement_order_buttons = [
        Button((WIDTH - 365, 672, 110, 36), "MOVE", "N", lambda: set_current_order("Normal")),
        Button((WIDTH - 245, 672, 110, 36), "QUICK", "Q", lambda: set_current_order("Quick")),
        Button((WIDTH - 125, 672, 110, 36), "FAST", "F", lambda: set_current_order("Fast")),
        Button((WIDTH - 365, 715, 110, 36), "SNEAK", "S", lambda: set_current_order("Sneak")),
        Button((WIDTH - 245, 715, 110, 36), "ASSAULT", "A", lambda: set_current_order("Assault")),
        Button((WIDTH - 125, 715, 110, 36), "HALT", "H", lambda: set_current_order("Halt")),
    ]

    combat_order_buttons = [
        Button((WIDTH - 365, 672, 110, 36), "FIRE", "Z", lambda: set_current_order("Fire")),
        Button((WIDTH - 245, 672, 110, 36), "AREA FIRE", "X", lambda: set_current_order("AreaFire")),
        Button((WIDTH - 125, 672, 110, 36), "SMOKE", "G", lambda: set_current_order("Smoke")),
        Button((WIDTH - 365, 715, 110, 36), "CEASE FIRE", "C", lambda: set_current_order("Halt")),
        Button((WIDTH - 245, 715, 110, 36), "FLARE", "H", lambda: set_current_order("Flare")),
        Button((WIDTH - 125, 715, 110, 36), "HIDE", "K", lambda: set_current_order("Sneak")),
    ]

    special_order_buttons = [
        Button((WIDTH - 365, 672, 110, 36), "MOUNT", "M", lambda: set_current_order("Mount")),
        Button((WIDTH - 245, 672, 110, 36), "DISMOUNT", "U", lambda: set_current_order("Dismount")),
        Button((WIDTH - 125, 672, 110, 36), "DIG IN", "B", lambda: set_current_order("Trench")),
        Button((WIDTH - 365, 715, 110, 36), "CALL ARTY", "T", lambda: None),
        Button((WIDTH - 245, 715, 110, 36), "AIR STRIKE", "Y", lambda: None),
        Button((WIDTH - 125, 715, 110, 36), "MEDIC AID", "P", lambda: None),
    ]

    spawn_blue_btn = Button((375, 646, 175, 24), "+ BLUE FIRETEAM", "B", lambda: spawn_squad("blue", random.randint(1, 4), random.randint(1, 14)))
    spawn_red_btn  = Button((560, 646, 175, 24), "+ RED OPFOR", "R", lambda: spawn_squad("red", random.randint(26, 30), random.randint(1, 14)))

    font_title = pygame.font.SysFont("Jokerman", 36)
    font_big = pygame.font.SysFont("Verdana", 14, bold=True)
    font_normal = pygame.font.SysFont("Verdana", 13, bold=False)
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
                    forces_btn.handle_click(mpos)
                    help_btn.handle_click(mpos)
                elif game_state == "HELP":
                    back_btn.handle_click(mpos)
                elif game_state == "FORCE_SELECTOR":
                    if event.button == 1:
                        for i, nat in enumerate(force_selector.nations):
                            bx = 20 + (i % 3) * 115
                            by = 120 + (i // 3) * 36
                            if pygame.Rect(bx, by, 108, 30).collidepoint(mpos):
                                force_selector.selected_nation = nat

                        for j, cat in enumerate(force_selector.categories):
                            bx = 380 + j * 125
                            by = 120
                            if pygame.Rect(bx, by, 118, 30).collidepoint(mpos):
                                force_selector.selected_category = cat

                        cat_items = force_selector.catalog.get(force_selector.selected_category, [])
                        for k, itm in enumerate(cat_items):
                            ir = pygame.Rect(380, 165 + k * 45, 520, 38)
                            if ir.collidepoint(mpos):
                                force_selector.add_item(itm)

                        for idx in range(len(force_selector.purchased_units)):
                            del_r = pygame.Rect(1230, 165 + idx * 30, 25, 24)
                            if del_r.collidepoint(mpos):
                                force_selector.remove_item(idx)
                                break

                        if pygame.Rect(WIDTH - 240, HEIGHT - 55, 220, 42).collidepoint(mpos):
                            deploy_selected_forces()

                        if pygame.Rect(20, HEIGHT - 55, 140, 42).collidepoint(mpos):
                            game_state = "START"

                elif game_state == "DEMO":
                    if event.button == 1:
                        clicked_ui = False
                        if pygame.Rect(910, 648, 110, 20).collidepoint(mpos):
                            current_ui_tab = "MOVEMENT"
                            clicked_ui = True
                        elif pygame.Rect(1025, 648, 110, 20).collidepoint(mpos):
                            current_ui_tab = "COMBAT"
                            clicked_ui = True
                        elif pygame.Rect(1140, 648, 110, 20).collidepoint(mpos):
                            current_ui_tab = "SPECIAL"
                            clicked_ui = True

                        active_order_btns = movement_order_buttons if current_ui_tab == "MOVEMENT" else (combat_order_buttons if current_ui_tab == "COMBAT" else special_order_buttons)
                        for btn in active_order_btns + [spawn_blue_btn, spawn_red_btn]:
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

            elif event.type == pygame.KEYDOWN and game_state == "DEMO" and selected_team:
                if event.key == pygame.K_n: set_current_order("Normal")
                elif event.key == pygame.K_q: set_current_order("Quick")
                elif event.key == pygame.K_f: set_current_order("Fast")
                elif event.key == pygame.K_s: set_current_order("Sneak")
                elif event.key == pygame.K_a: set_current_order("Assault")
                elif event.key == pygame.K_h: set_current_order("Halt")
                elif event.key == pygame.K_m: set_current_order("Mount")
                elif event.key == pygame.K_u: set_current_order("Dismount")

        if game_state == "DEMO":
            collision_mangr.update(units_group, buildings_group)
            projectiles_group.update()
            for t in all_teams:
                t.update(tactical_grid, all_teams, projectiles_group)
            damage_mangr.update(projectiles_group, units_group)

        screen.fill((25, 27, 25))

        if game_state == "START":
            title = font_title.render("Halloween game that is now 5 days late", True, (230, 225, 210))
            sub = font_big.render("I swear those black dots on kfc chicken aren't peppers", True, (165, 175, 150))
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3 - 30)))
            screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 15)))
            start_btn.draw(screen, font_big, font_subscript)
            forces_btn.draw(screen, font_big, font_subscript)
            help_btn.draw(screen, font_big, font_subscript)

        elif game_state == "FORCE_SELECTOR":
            hdr_rect = pygame.Rect(0, 0, WIDTH, 50)
            pygame.draw.rect(screen, (34, 42, 36), hdr_rect)
            pygame.draw.line(screen, (80, 95, 80), (0, 50), (WIDTH, 50), 2)

            team_a_rect = pygame.Rect(20, 10, 100, 32)
            pygame.draw.rect(screen, (55, 75, 55) if force_selector.active_team == "Team A" else (35, 45, 38), team_a_rect)
            screen.blit(font_big.render("Team A", True, (255, 255, 200)), (35, 16))

            team_b_rect = pygame.Rect(130, 10, 100, 32)
            pygame.draw.rect(screen, (55, 75, 55) if force_selector.active_team == "Team B" else (35, 45, 38), team_b_rect)
            screen.blit(font_big.render("Team B", True, (200, 210, 200)), (145, 16))

            b_str = f"BUDGET: {force_selector.budget_req} RP / {force_selector.budget_rar} RarP    |    SPENT: {force_selector.spent_req} RP / {force_selector.spent_rar} RarP    |    REMAIN: {force_selector.remain_req} RP / {force_selector.remain_rar} RarP"
            screen.blit(font_normal.render(b_str, True, (230, 240, 180)), (280, 16))

            nat_panel = pygame.Rect(15, 65, 350, 660)
            pygame.draw.rect(screen, (28, 34, 30), nat_panel)
            pygame.draw.rect(screen, (60, 72, 60), nat_panel, 1)
            screen.blit(font_big.render("FACTION / NATION", True, (210, 220, 190)), (25, 78))

            for i, nat in enumerate(force_selector.nations):
                bx = 25 + (i % 2) * 165
                by = 110 + (i // 2) * 40
                n_rect = pygame.Rect(bx, by, 155, 32)
                is_sel = (force_selector.selected_nation == nat)
                pygame.draw.rect(screen, (60, 80, 55) if is_sel else (40, 48, 42), n_rect)
                pygame.draw.rect(screen, (150, 180, 130) if is_sel else (70, 85, 70), n_rect, 1)
                screen.blit(font_subscript.render(nat, True, (255, 255, 255) if is_sel else (180, 190, 180)), (bx + 8, by + 8))

            screen.blit(font_big.render("FORMATION MODIFIERS", True, (210, 220, 190)), (25, 280))
            mods = [
                ("Unit Experience:", "PLACEHOLDER"),
                ("Motivation:", "PLACEHOLDER"),
                ("Fitness:", "PLACEHOLDER"),
                ("Leadership:", "PLACEHOLDER"),
            ]
            for m_idx, (k, val) in enumerate(mods):
                screen.blit(font_normal.render(k, True, (160, 175, 160)), (25, 315 + m_idx * 40))
                screen.blit(font_subscript.render(val, True, (240, 240, 160)), (35, 335 + m_idx * 40))

            preview_box = pygame.Rect(25, 490, 330, 150)
            pygame.draw.rect(screen, (20, 25, 22), preview_box)
            pygame.draw.rect(screen, (55, 70, 55), preview_box, 1)
            screen.blit(font_big.render("[Preview Map / Suggest]", True, (180, 200, 170)), (35, 500))
            screen.blit(font_subscript.render("Sector: Central Valley - High Cover", True, (140, 150, 140)), (35, 525))
            screen.blit(font_subscript.render("Grid: 40px Tactical / Elevation Mode", True, (140, 150, 140)), (35, 545))

            cat_panel = pygame.Rect(375, 65, 890, 45)
            pygame.draw.rect(screen, (28, 34, 30), cat_panel)
            pygame.draw.rect(screen, (60, 72, 60), cat_panel, 1)
            for j, cat in enumerate(force_selector.categories):
                cbx = 385 + j * 175
                c_rect = pygame.Rect(cbx, 72, 165, 32)
                is_c_sel = (force_selector.selected_category == cat)
                pygame.draw.rect(screen, (65, 85, 60) if is_c_sel else (40, 48, 42), c_rect)
                pygame.draw.rect(screen, (160, 200, 140) if is_c_sel else (70, 85, 70), c_rect, 1)
                screen.blit(font_normal.render(cat, True, (255, 255, 255) if is_c_sel else (180, 190, 180)), (cbx + 14, 78))

            items_panel = pygame.Rect(375, 120, 540, 605)
            pygame.draw.rect(screen, (24, 28, 25), items_panel)
            pygame.draw.rect(screen, (55, 65, 55), items_panel, 1)
            screen.blit(font_big.render(f"AVAILABLE: {force_selector.selected_category.upper()}", True, (200, 215, 180)), (385, 130))

            cat_items = force_selector.catalog.get(force_selector.selected_category, [])
            for k, itm in enumerate(cat_items):
                ir = pygame.Rect(385, 160 + k * 52, 520, 44)
                pygame.draw.rect(screen, (34, 40, 36), ir)
                pygame.draw.rect(screen, (65, 80, 65), ir, 1)
                screen.blit(font_big.render(itm["name"], True, (230, 235, 220)), (395, 165 + k * 52))
                pts_txt = f"Cost: {itm['req']} RP  |  Rarity: {itm['rar']} RarP"
                screen.blit(font_subscript.render(pts_txt, True, (160, 220, 160)), (395, 184 + k * 52))

                sub_txt = " + ".join(itm.get("subordinates", itm.get("loadout", [itm.get("desc", "")]))[:2])
                if sub_txt:
                    screen.blit(font_subscript.render(f"({sub_txt})", True, (180, 180, 140)), (630, 172 + k * 52))

                add_lbl = font_subscript.render("[+ ADD]", True, (255, 240, 120))
                screen.blit(add_lbl, (840, 175 + k * 52))

            roster_panel = pygame.Rect(925, 120, 340, 605)
            pygame.draw.rect(screen, (24, 28, 25), roster_panel)
            pygame.draw.rect(screen, (55, 65, 55), roster_panel, 1)
            screen.blit(font_big.render("SELECTED OOB / ROSTER", True, (200, 215, 180)), (935, 130))

            if not force_selector.purchased_units:
                screen.blit(font_normal.render("No units selected.", True, (120, 130, 120)), (940, 170))
                screen.blit(font_subscript.render("Click items on the left to add to roster.", True, (100, 110, 100)), (940, 195))
            else:
                for idx, p_item in enumerate(force_selector.purchased_units):
                    pr_box = pygame.Rect(935, 160 + idx * 36, 320, 30)
                    pygame.draw.rect(screen, (32, 38, 34), pr_box)
                    screen.blit(font_subscript.render(f"{p_item['name']}", True, (220, 230, 220)), (942, 168 + idx * 36))
                    screen.blit(font_subscript.render(f"{p_item['req']} RP", True, (150, 210, 150)), (1150, 168 + idx * 36))
                    del_lbl = font_subscript.render("[X]", True, (240, 90, 80))
                    screen.blit(del_lbl, (1235, 168 + idx * 36))

            b_btn = pygame.Rect(20, HEIGHT - 55, 140, 42)
            pygame.draw.rect(screen, (45, 50, 46), b_btn)
            screen.blit(font_big.render("<< MENU", True, (210, 220, 210)), (45, HEIGHT - 42))

            deploy_btn = pygame.Rect(WIDTH - 240, HEIGHT - 55, 220, 42)
            pygame.draw.rect(screen, (50, 80, 45), deploy_btn)
            pygame.draw.rect(screen, (140, 220, 120), deploy_btn, 2)
            screen.blit(font_big.render("DEPLOY TO BATTLE >>", True, (255, 255, 180)), (WIDTH - 225, HEIGHT - 42))

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
                ("5. Assault: Gathers the squad and attacks; halts to engage.", False),
                ("6. Halt: Stop moving immediately.", False),
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

            shortcuts_panel = pygame.Rect(10, 10, 220, 240)
            pygame.draw.rect(screen, (24, 28, 25), shortcuts_panel)
            pygame.draw.rect(screen, (55, 65, 55), shortcuts_panel, 1)
            screen.blit(font_subscript.render("TACTICAL SHORTCUTS", True, (210, 220, 180)), (18, 14))

            sc_items = [
                ("Mount", "M"), ("Dismount", "U"),
                ("Fire", "A"), ("Area Fire", "Shift+A"),
                ("Artillery Call", "T"), ("Fixed Wing Air", "Y"),
                ("Helicopter Call", "I"), ("Smoke Screen", "G"),
                ("Signal Flare", "H"), ("Entrenchment", "B")
            ]
            for s_idx, (act, sc_k) in enumerate(sc_items):
                sy = 34 + s_idx * 19
                screen.blit(font_subscript.render(act, True, (190, 200, 190)), (18, sy))
                screen.blit(font_subscript.render(f"[{sc_k}]", True, (230, 220, 140)), (170, sy))

            console_rect = pygame.Rect(0, 640, WIDTH, 160)
            pygame.draw.rect(screen, (28, 35, 31), console_rect)
            pygame.draw.line(screen, (70, 80, 70), (0, 640), (WIDTH, 640), 2)
            panel_left = pygame.Rect(8, 646, 350, 146)
            pygame.draw.rect(screen, (24, 28, 25), panel_left)
            pygame.draw.rect(screen, (55, 65, 55), panel_left, 1)

            unit_box = pygame.Rect(18, 656, 46, 34)
            pygame.draw.rect(screen, (40, 50, 42), unit_box)
            pygame.draw.rect(screen, (130, 150, 130), unit_box, 1)
            pygame.draw.line(screen, (130, 150, 130), unit_box.topleft, unit_box.bottomright, 1)
            pygame.draw.line(screen, (130, 150, 130), unit_box.bottomleft, unit_box.topright, 1)
            pygame.draw.circle(screen, (200, 220, 200), (41, 673), 3)

            if selected_team:
                team_clr = (140, 190, 255) if selected_team.team == "blue" else (255, 140, 140)
                name_lbl = font_big.render(selected_team.name, True, team_clr)
                lead_lbl = font_subscript.render(f"HQ: {selected_team.squad.leader.name} [Leader]", True, (180, 190, 180))
                c2_lbl   = font_subscript.render("C2 LINK: VOICE / SIGHT (100%)", True, (120, 220, 120))
                screen.blit(name_lbl, (74, 656))
                screen.blit(lead_lbl, (74, 674))
                screen.blit(c2_lbl, (74, 690))

                supp_txt = font_subscript.render("SUPPRESSION / MORALE", True, (160, 170, 160))
                screen.blit(supp_txt, (18, 712))

                wedge_pts = [(18, 746), (180, 746), (180, 730)]
                pygame.draw.polygon(screen, (20, 25, 20), wedge_pts)
                pygame.draw.polygon(screen, (60, 70, 60), wedge_pts, 1)

                supp_pct = min(1.0, selected_team.suppression / 100.0)
                if supp_pct > 0:
                    w_fill = int(162 * supp_pct)
                    fill_pts = [(18, 746), (18 + w_fill, 746), (18 + w_fill, 746 - int(16 * supp_pct))]
                    fill_clr = (220, 70, 50) if supp_pct > 0.6 else (230, 180, 40)
                    pygame.draw.polygon(screen, fill_clr, fill_pts)

                morale_val = selected_team.avg_morale()
                state_str = "OK" if morale_val > 70 else ("CAUTIOUS" if morale_val > 40 else "SHAKEN")
                state_lbl = font_big.render(f"MORALE: {state_str}", True, (210, 215, 180))
                action_lbl = font_subscript.render(f"ACTION: {selected_team.current_action.upper()}", True, (180, 220, 140))
                screen.blit(state_lbl, (210, 712))
                screen.blit(action_lbl, (18, 755))
            else:
                lbl_none = font_normal.render("NO UNIT SELECTED", True, (120, 130, 120))
                screen.blit(lbl_none, (74, 665))
                sub_none = font_subscript.render("Left-click unit to inspect and command", True, (90, 100, 90))
                screen.blit(sub_none, (18, 715))

            panel_center = pygame.Rect(366, 646, 530, 146)
            pygame.draw.rect(screen, (24, 28, 25), panel_center)
            pygame.draw.rect(screen, (55, 65, 55), panel_center, 1)

            spawn_blue_btn.draw(screen, font_normal, font_subscript)
            spawn_red_btn.draw(screen, font_normal, font_subscript)

            if selected_team:
                roster_hdr = font_big.render("Squad Members & Equipment (Cost: %d RP / %d RarP)" % selected_team.calculate_points(), True, (165, 175, 150))
                screen.blit(roster_hdr, (376, 678))
                y_soldier = 700
                for s in selected_team.members:
                    cond_clr = (140, 220, 140) if s.condition > 150 else ((240, 180, 50) if s.condition > 50 else (220, 60, 60))
                    cond_txt = "FIT" if s.condition > 150 else ("Shot" if s.condition > 50 else "KIRKED!")
                    s_str = f"{s.rank} {s.name}  --  {s.weapon} [G: {s.gun.req_points}RP]"
                    txt_s = font_subscript.render(s_str, True, (210, 215, 210))
                    txt_c = font_subscript.render(f"[{cond_txt}]", True, cond_clr)
                    screen.blit(txt_s, (376, y_soldier))
                    screen.blit(txt_c, (640, y_soldier))
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
            pygame.draw.rect(screen, (55, 68, 55) if current_ui_tab == "MOVEMENT" else (32, 38, 33), tab_mov)
            pygame.draw.rect(screen, (100, 120, 100), tab_mov, 1)
            screen.blit(font_big.render("MOVEMENT", True, (255, 250, 180) if current_ui_tab == "MOVEMENT" else (140, 150, 140)), (922, 650))

            tab_com = pygame.Rect(1025, 648, 110, 20)
            pygame.draw.rect(screen, (55, 68, 55) if current_ui_tab == "COMBAT" else (32, 38, 33), tab_com)
            pygame.draw.rect(screen, (100, 120, 100), tab_com, 1)
            screen.blit(font_big.render("COMBAT", True, (255, 250, 180) if current_ui_tab == "COMBAT" else (140, 150, 140)), (1045, 650))

            tab_spc = pygame.Rect(1140, 648, 110, 20)
            pygame.draw.rect(screen, (55, 68, 55) if current_ui_tab == "SPECIAL" else (32, 38, 33), tab_spc)
            pygame.draw.rect(screen, (100, 120, 100), tab_spc, 1)
            screen.blit(font_big.render("SPECIAL", True, (255, 250, 180) if current_ui_tab == "SPECIAL" else (140, 150, 140)), (1155, 650))

            active_buttons = movement_order_buttons if current_ui_tab == "MOVEMENT" else (combat_order_buttons if current_ui_tab == "COMBAT" else special_order_buttons)
            for btn in active_buttons:
                btn_order_map = {
                    "MOVE": "Normal", "QUICK": "Quick", "FAST": "Fast",
                    "SNEAK": "Sneak", "ASSAULT": "Assault", "HALT": "Halt",
                    "MOUNT": "Mount", "DISMOUNT": "Dismount"
                }
                btn.active = bool(selected_team and selected_team.move_order == btn_order_map.get(btn.title))
                btn.draw(screen, font_normal, font_subscript)

            minimap_rect = pygame.Rect(WIDTH - 150, 10, 140, 95)
            pygame.draw.rect(screen, (20, 25, 20), minimap_rect)
            pygame.draw.rect(screen, (70, 85, 70), minimap_rect, 1)
            screen.blit(font_subscript.render("MINIMAP", True, (160, 180, 160)), (WIDTH - 145, 14))

            for u in all_teams:
                mx = WIDTH - 150 + int((u.pos.x / WIDTH) * 140)
                my = 10 + int((u.pos.y / 640) * 95)
                m_clr = (60, 130, 255) if u.team == "blue" else (240, 60, 60)
                pygame.draw.rect(screen, m_clr, (mx - 2, my - 2, 4, 4))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
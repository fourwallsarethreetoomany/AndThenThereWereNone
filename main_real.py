import random
import pygame
import asyncio
try: #try to not fail ts
    from setup import WIDTH, HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS
except ImportError:
    WIDTH, HEIGHT = 1280, 800
    CELL_SIZE = 150
    GRID_COLS = (WIDTH // CELL_SIZE) + 1 
    GRID_ROWS = max(8, (HEIGHT // CELL_SIZE) + 2)
 
if GRID_ROWS < 8:
    GRID_ROWS = 8

from combat import DamageManager, CollisionManager
from equipment import Gun, Grenade, Radio, Binoculars   
from vehicles import Vehicle, T55, BRDM2                
from unit import Soldier, Squad, InfantryTeam
from grid import TacticalGrid, astar_pathfind
from ui_button import Button
from ui_forceselector import ForceSelector

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AndThereWereNone")
clock = pygame.time.Clock()
 
CLR_BG_OBSIDIAN    = (12, 10, 12)
CLR_PANEL_CRIMSON  = (28, 11, 15)
CLR_PANEL_BORDER   = (84, 22, 31)
CLR_CRIMSON_BRIGHT = (185, 34, 48)
CLR_CRIMSON_MUTED  = (125, 26, 36)
CLR_TEXT_LIGHT     = (238, 230, 230)
CLR_TEXT_MUTED     = (170, 148, 152)
CLR_TEXT_GOLD      = (232, 190, 100)
CLR_ACCENT_RED     = (220, 48, 60)
 
ACTION_PHASE_TICKS = 30 * 60

async def main():
    damage_mangr = DamageManager()
    collision_mangr = CollisionManager()
    units_group = pygame.sprite.Group()
    projectiles_group = pygame.sprite.Group()
    buildings_group = pygame.sprite.Group()
    casualties_group = pygame.sprite.Group()
    effects_group = pygame.sprite.Group()   

    game_state = "START"  # main menu
    tactical_grid = TacticalGrid(GRID_COLS, GRID_ROWS)

    camera_x = 0.0
    camera_y = 0.0
    camera_speed = 10.0

    # [ADD START] Turn & Phase state (WEGO: ORDER -> 30s ACTION -> ORDER)
    turn_number = 1
    turn_phase = "ORDER"
    action_ticks_remaining = 0
    # [ADD END]

    all_teams = []
    selected_squad = None
    force_selector = ForceSelector()
    current_ui_tab = "MOVEMENT"
    debug_mode = False

    selected_mission = { 
        "title": "Placeholder",
        "theater": "Placeholder",
        "objective": "Placeholder",
        "intel": "Placeholder",
        "difficulty": "1"
    }

    # [ADD START] Run TacAI spotting and range estimation during Order Phase
    def run_order_phase_tacai():
        for unit in all_teams:
            if unit.total_health() > 0 and hasattr(unit, "update_tacai_spotting"):
                unit.update_tacai_spotting(tactical_grid, all_teams, force_estimate=True)
    # [ADD END]

    def spawn_squad(team_side, gx, gy):
        ak_gun = Gun("Placeholder", 7.62, "Rifle", 8, 0)
        rpd_gun = Gun("Placeholder MG", 7.62, "MachineGun", 16, 4)
        f1_grenades = Grenade("Placeholder grenade", 2, 4, 0)
        squad_radio = Radio("Placeholder radio", 100, 15, 5)
        field_binos = Binoculars("B-8x30 Binoculars")  # [ADD] Leader carries Binoculars

        leader = Soldier("Placeholder", "Placeholder rank", "Placeholder", ak_gun, f1_grenades, squad_radio, binoculars_obj=field_binos)
        squad = Squad(leader)

        # [EDIT] Pass effects_group to InfantryTeam
        team_a = InfantryTeam(f"{team_side.upper()} Team A", squad, team_side, gx, gy, casualties_group=casualties_group, effects_group=effects_group)
        team_a.add_soldier(leader)
        team_a.add_soldier(Soldier("Placeholder Placeholder", "Placeholder rank", "Placeholder MG", rpd_gun, f1_grenades))
        team_a.add_soldier(Soldier("PlaceholderPlaceholder", "Placeholder rank", "Placeholder", ak_gun, f1_grenades))

        team_b = InfantryTeam(f"{team_side.upper()} Team B", squad, team_side, gx + 1, gy, casualties_group=casualties_group, effects_group=effects_group)
        team_b.add_soldier(Soldier("Placeholder", "Placeholder rank", "Placeholder", ak_gun, f1_grenades))
        team_b.add_soldier(Soldier("Placeholder", "Placeholder rank", "Placeholder", ak_gun, f1_grenades))

        squad.fireteams.extend([team_a, team_b])

        team_a.formation_spread = 24
        team_b.formation_spread = 24

        for t in [team_a, team_b]:
            c = tactical_grid.get_cell(t.gx, t.gy)
            if c:
                c.occupant = t
            units_group.add(t)
            all_teams.append(t)

        if turn_phase == "ORDER":
            run_order_phase_tacai()

        return squad

    # [ADD START] Helper to spawn playable tactical vehicles (T55, BRDM2, etc.)
    def spawn_vehicle(veh_cls, team_side, gx, gy):
        w_pos = tactical_grid.grid_to_world_center(gx, gy)
        veh = veh_cls(w_pos.x, w_pos.y, team=team_side, effects_group=effects_group)
        veh.gx = gx
        veh.gy = gy
        if team_side == "red":
            veh.angle = 180
            veh.turret_angle = 180
            veh.image = pygame.transform.rotate(veh.original_image, -veh.angle)
            veh.rect = veh.image.get_rect(center=(int(veh.pos.x), int(veh.pos.y)))
        c = tactical_grid.get_cell(gx, gy)
        if c:
            c.occupant = veh
        units_group.add(veh)
        all_teams.append(veh)
        if turn_phase == "ORDER":
            run_order_phase_tacai()
        return veh
    # [ADD END]

    def deploy_selected_forces():
        nonlocal game_state, selected_squad, camera_x, camera_y, turn_number, turn_phase, action_ticks_remaining
        all_teams.clear()
        units_group.empty()
        projectiles_group.empty()
        casualties_group.empty()
        effects_group.empty()  # [ADD] Clear visual effects on deploy
        selected_squad = None
        camera_x, camera_y = 0.0, 0.0

        # [ADD START] Initialize Turn 1 in ORDER phase
        turn_number = 1
        turn_phase = "ORDER"
        action_ticks_remaining = 0
        # [ADD END]

        if not force_selector.purchased_units:
            # [EDIT START] Default skirmish includes Infantry, T-55, and BRDM-2 on both sides
            spawn_squad("blue", 1, 1)
            spawn_vehicle(T55, "blue", 1, 4)
            spawn_vehicle(BRDM2, "blue", 2, 5)

            spawn_squad("red", max(2, GRID_COLS - 3), 1)
            spawn_vehicle(T55, "red", max(2, GRID_COLS - 2), 4)
            spawn_vehicle(BRDM2, "red", max(2, GRID_COLS - 3), 5)

            run_order_phase_tacai()
            game_state = "GAME"
            return
            # [EDIT END]

        spawn_x = 1
        spawn_y = 1

        for item in force_selector.purchased_units:
            u_type = item.get("type")

            if u_type == "formation":
                spawn_squad("blue", spawn_x, spawn_y)
                spawn_y = (spawn_y + 2) % (GRID_ROWS - 2) + 1
                if spawn_y <= 2:
                    spawn_x += 2

            elif u_type == "vehicle":
                # [EDIT START] Spawn purchased vehicles directly as active tactical Vehicle units
                cls = item.get("cls", Vehicle)
                count = 3 if item.get("is_full", False) else 1
                for _ in range(count):
                    spawn_vehicle(cls, "blue", spawn_x, spawn_y)
                    spawn_y = (spawn_y + 1) % (GRID_ROWS - 2) + 1
                # [EDIT END]

        spawn_squad("red", max(2, GRID_COLS - 3), 1)
        spawn_vehicle(T55, "red", max(2, GRID_COLS - 2), 4)
        spawn_vehicle(BRDM2, "red", max(2, GRID_COLS - 3), 5)

        run_order_phase_tacai()
        game_state = "GAME"

    # [ADD START] Turn transition callback: ORDER -> 30s ACTION phase
    def start_action_phase():
        nonlocal turn_phase, action_ticks_remaining
        if game_state == "GAME" and turn_phase == "ORDER":
            turn_phase = "ACTION"
            action_ticks_remaining = ACTION_PHASE_TICKS
    # [ADD END]

    def select_team_and_squad(team):
        nonlocal selected_squad
        for t in all_teams:
            t.selected = False
        if team:
            selected_squad = team.squad
            for t in selected_squad.fireteams:
                t.selected = True
        else:
            selected_squad = None

    def set_current_order(order_name):
        # [EDIT] Orders can only be changed during the ORDER phase
        if turn_phase != "ORDER":
            return
        if selected_squad:
            for ft in selected_squad.fireteams:
                ft.set_order(order_name)

    # Navigation Callbacks
    def open_mission_select():
        nonlocal game_state
        game_state = "MISSION_SELECT"

    def open_force_selector():
        nonlocal game_state
        game_state = "FORCE_SELECTOR"

    def open_help():
        nonlocal game_state
        game_state = "HELP"

    def back_to_menu():
        nonlocal game_state
        game_state = "START"

    start_btn = Button((WIDTH // 2 - 130, HEIGHT // 2 - 70, 260, 48), "Level Select", "ENTER", open_mission_select)
    forces_btn = Button((WIDTH // 2 - 130, HEIGHT // 2 - 10, 260, 48), "Force Selector", "F2", open_force_selector)
    help_btn  = Button((WIDTH // 2 - 130, HEIGHT // 2 + 50, 260, 48), "Tutorial for Dummies", "F1", open_help)
    back_btn  = Button((WIDTH // 2 - 100, HEIGHT - 90, 200, 45), "Go Bacc", "ESC", back_to_menu)

    # Mission Select Buttons (Clipboard)
    clip_launch_btn = Button((WIDTH // 2 + 40, HEIGHT - 130, 240, 46), "Edit Units", "", open_force_selector)
    clip_quick_btn  = Button((WIDTH // 2 - 280, HEIGHT - 130, 240, 46), "Use what I used", "", deploy_selected_forces)
    clip_back_btn   = Button((WIDTH // 2 - 80, HEIGHT - 75, 160, 36), "<< To Menu", "ESC", back_to_menu)

    # [ADD] Top HUD button to end Order Phase and start 30-second Action Phase
    end_orders_btn = Button((WIDTH // 2 + 120, 8, 195, 36), "START ACTION", "SPACE", start_action_phase)

    # Tactical UI Orders
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
# testing only, removing later
    spawn_blue_btn = Button((375, 646, 175, 24), "+ BLUE FIRETEAM", "B", lambda: spawn_squad("blue", random.randint(0, 2), random.randint(0, GRID_ROWS - 2)))
    spawn_red_btn  = Button((560, 646, 175, 24), "+ RED OPFOR", "R", lambda: spawn_squad("red", random.randint(max(0, GRID_COLS - 3), GRID_COLS - 1), random.randint(0, GRID_ROWS - 2)))

    font_title = pygame.font.SysFont("Impact", 42)
    font_header = pygame.font.SysFont("Verdana", 18, bold=True)
    font_big = pygame.font.SysFont("Verdana", 14, bold=True)
    font_normal = pygame.font.SysFont("Verdana", 13, bold=False)
    font_subscript = pygame.font.SysFont("Verdana", 11)
    font_mono = pygame.font.SysFont("Courier New", 14, bold=True)
    font_debug = pygame.font.SysFont("Consolas", 32, bold=True)
    font_wingdings = pygame.font.SysFont("Wingdings", 18, bold=True) #unused, maybe for funnies or icons
    font_bullshit = pygame.font.SysFont("Wingdings", 12, bold=True) #unused, maybe for funnies or icons

    running = True
    while running:
        mpos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSLASH:
                    debug_mode = not debug_mode

                # [ADD] SPACE starts the 30s Action Phase from Order Phase
                if game_state == "GAME" and event.key == pygame.K_SPACE and turn_phase == "ORDER":
                    start_action_phase()

                if game_state == "GAME" and selected_squad and turn_phase == "ORDER":
                    if event.key == pygame.K_n: set_current_order("Normal")
                    elif event.key == pygame.K_q: set_current_order("Quick")
                    elif event.key == pygame.K_f: set_current_order("Fast")
                    elif event.key == pygame.K_s: set_current_order("Sneak")
                    elif event.key == pygame.K_a: set_current_order("Assault")
                    elif event.key == pygame.K_h: set_current_order("Halt")
                    elif event.key == pygame.K_m: set_current_order("Mount")
                    elif event.key == pygame.K_u: set_current_order("Dismount")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "START":
                    start_btn.handle_click(mpos)
                    forces_btn.handle_click(mpos)
                    help_btn.handle_click(mpos)

                elif game_state == "MISSION_SELECT":
                    clip_launch_btn.handle_click(mpos)
                    clip_quick_btn.handle_click(mpos)
                    clip_back_btn.handle_click(mpos)

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
                            game_state = "MISSION_SELECT"

                elif game_state == "GAME":
                    if event.button == 1:
                        clicked_ui = False

                        # [ADD] Handle clicking the top START ACTION button during ORDER phase
                        if turn_phase == "ORDER" and end_orders_btn.handle_click(mpos):
                            clicked_ui = True

                        if not clicked_ui and pygame.Rect(910, 648, 110, 20).collidepoint(mpos):
                            current_ui_tab = "MOVEMENT"
                            clicked_ui = True
                        elif not clicked_ui and pygame.Rect(1025, 648, 110, 20).collidepoint(mpos):
                            current_ui_tab = "COMBAT"
                            clicked_ui = True
                        elif not clicked_ui and pygame.Rect(1140, 648, 110, 20).collidepoint(mpos):
                            current_ui_tab = "SPECIAL"
                            clicked_ui = True

                        if not clicked_ui:
                            active_order_btns = movement_order_buttons if current_ui_tab == "MOVEMENT" else (combat_order_buttons if current_ui_tab == "COMBAT" else special_order_buttons)
                            for btn in active_order_btns + [spawn_blue_btn, spawn_red_btn]:
                                if btn.handle_click(mpos):
                                    clicked_ui = True
                                    break

                        if not clicked_ui and mpos[1] < 640:
                            world_mpos = pygame.Vector2(mpos[0] + camera_x, mpos[1] + camera_y)
                            clicked_unit = None
                            for t in all_teams:
                                if t.total_health() <= 0:
                                    continue
                                if t.pos.distance_to(world_mpos) <= t.collision_radius + 15:
                                    clicked_unit = t
                                    break
                                if hasattr(t, "get_soldier_world_pos"):
                                    for idx, sm in enumerate(t.members):
                                        m_pos = t.get_soldier_world_pos(idx)
                                        if m_pos.distance_to(world_mpos) <= 14:
                                            clicked_unit = t
                                            break
                                if clicked_unit:
                                    break

                            if clicked_unit:
                                select_team_and_squad(clicked_unit)
                            # [EDIT] Pathfinding occurs only during the ORDER phase
                            elif selected_squad and turn_phase == "ORDER":
                                gx, gy = tactical_grid.world_to_grid(world_mpos.x, world_mpos.y)
                                for offset_idx, ft in enumerate(selected_squad.fireteams):
                                    tgt_gx = min(GRID_COLS - 1, max(0, gx + (offset_idx % 2)))
                                    tgt_gy = min(GRID_ROWS - 1, max(0, gy + (offset_idx // 2)))
                                    p = astar_pathfind(tactical_grid, ft.gx, ft.gy, tgt_gx, tgt_gy, ft.move_order, ft)
                                    if p:
                                        ft.path = p

                    elif event.button == 3:
                        select_team_and_squad(None)

        if game_state == "GAME":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                camera_x -= camera_speed
            if keys[pygame.K_RIGHT]:
                camera_x += camera_speed
            if keys[pygame.K_UP]:
                camera_y -= camera_speed
            if keys[pygame.K_DOWN]:
                camera_y += camera_speed
            max_cam_x = max(0, tactical_grid.cols * CELL_SIZE - WIDTH)
            max_cam_y = max(0, tactical_grid.rows * CELL_SIZE - 640)
            camera_x = max(0.0, min(camera_x, float(max_cam_x)))
            camera_y = max(0.0, min(camera_y, float(max_cam_y)))

            # [EDIT START] Simulation runs only during the 30-second ACTION phase
            if turn_phase == "ACTION":
                collision_mangr.update(units_group, buildings_group)
                projectiles_group.update(all_teams)
                effects_group.update()
                for t in all_teams:
                    t.update(tactical_grid, all_teams, projectiles_group)
                damage_mangr.update(projectiles_group, units_group, effects_group)

                action_ticks_remaining -= 1
                if action_ticks_remaining <= 0:
                    turn_phase = "ORDER"
                    turn_number += 1
                    run_order_phase_tacai()
            # [EDIT END]

        screen.fill(CLR_BG_OBSIDIAN)
# mainmenu
        if game_state == "START":
            banner_rect = pygame.Rect(0, HEIGHT // 4 - 60, WIDTH, 130)
            pygame.draw.rect(screen, (22, 9, 12), banner_rect)
            pygame.draw.line(screen, CLR_PANEL_BORDER, banner_rect.topleft, banner_rect.topright, 2)
            pygame.draw.line(screen, CLR_PANEL_BORDER, banner_rect.bottomleft, banner_rect.bottomright, 2)

            title = font_title.render("[And Then There Were None]", True, (245, 230, 230)) # don't look up what Agatha Christie's original title
            sub = font_normal.render("PLACEHOLDER", True, CLR_TEXT_GOLD)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 4 - 15)))
            screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 4 + 32)))

            start_btn.draw(screen, font_big, font_subscript)
            forces_btn.draw(screen, font_big, font_subscript)
            help_btn.draw(screen, font_big, font_subscript)

            footer_txt = font_subscript.render(r"Press [ \ ] anywhere to toggle coordinate testing mode", True, CLR_TEXT_MUTED)
            screen.blit(footer_txt, footer_txt.get_rect(center=(WIDTH // 2, HEIGHT - 30)))

        elif game_state == "MISSION_SELECT":
            board_w, board_h = 760, 680
            board_rect = pygame.Rect((WIDTH - board_w) // 2, 40, board_w, board_h)
            pygame.draw.rect(screen, (35, 20, 22), board_rect, border_radius=12)
            pygame.draw.rect(screen, (60, 22, 28), board_rect, 3, border_radius=12)

            paper_rect = pygame.Rect(board_rect.x + 30, board_rect.y + 45, board_w - 60, board_h - 90)
            pygame.draw.rect(screen, (222, 212, 195), paper_rect)
            pygame.draw.rect(screen, (170, 155, 140), paper_rect, 1)

            clip_w, clip_h = 170, 48
            clip_rect = pygame.Rect(board_rect.centerx - clip_w // 2, board_rect.y + 12, clip_w, clip_h)
            pygame.draw.rect(screen, (50, 52, 58), clip_rect, border_radius=6)
            pygame.draw.rect(screen, (160, 165, 175), clip_rect, 2, border_radius=6)
            pygame.draw.circle(screen, (200, 205, 215), (clip_rect.left + 18, clip_rect.centery), 4)
            pygame.draw.circle(screen, (200, 205, 215), (clip_rect.right - 18, clip_rect.centery), 4)

            stamp_rect = pygame.Rect(paper_rect.right - 185, paper_rect.top + 25, 160, 42)
            pygame.draw.rect(screen, (180, 40, 50), stamp_rect, 2)
            stamp_txt = font_header.render("SENSITIVE", True, (180, 40, 50))
            screen.blit(stamp_txt, stamp_txt.get_rect(center=stamp_rect.center))

            px = paper_rect.x + 35
            py = paper_rect.y + 35

            screen.blit(font_header.render("Guide", True, (24, 20, 20)), (px, py))
            py += 35
            screen.blit(font_big.render(selected_mission["title"], True, (140, 20, 30)), (px, py))
            py += 26
            screen.blit(font_mono.render(f"THEATER: {selected_mission['theater']}", True, (50, 45, 45)), (px, py))
            py += 20
            screen.blit(font_mono.render(f"RISK EVL: {selected_mission['difficulty']}", True, (160, 40, 40)), (px, py))
            py += 32

            pygame.draw.line(screen, (180, 165, 150), (px, py), (paper_rect.right - 35, py), 2)
            py += 18

            screen.blit(font_big.render("Objectives:", True, (24, 20, 20)), (px, py))
            py += 24
            obj_lines = [
                "1. ELorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                "2. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                "3. iltam zumrā rašubti ilātim litta''id bēlet iššī rabīt igigī ištar zumrā rašubti ilātim litta''id bēlet ilī nišī rabīt igigī"
            ]
            for l in obj_lines:
                screen.blit(font_normal.render(l, True, (40, 35, 35)), (px + 10, py))
                py += 22

            py += 15
            screen.blit(font_big.render("Intelligence Report:", True, (24, 20, 20)), (px, py))
            py += 24
            intel_lines = [
                "- Unknown wall towards the north",
                "- Unidentified humanoid figures spotted peeling away the northern wall",
                "- Lorem Ipsum"
            ]
            for l in intel_lines:
                screen.blit(font_normal.render(l, True, (60, 50, 50)), (px + 10, py))
                py += 22

            clip_quick_btn.draw(screen, font_big, font_subscript)
            clip_launch_btn.draw(screen, font_big, font_subscript)
            clip_back_btn.draw(screen, font_normal, font_subscript)

        elif game_state == "FORCE_SELECTOR": #future idea: alignment/reputation. If you keep using the same veheicles from the same nations you get cheaper prices and eventually testing prototypes that give you overpowered bullshit
            hdr_rect = pygame.Rect(0, 0, WIDTH, 50)
            pygame.draw.rect(screen, CLR_PANEL_CRIMSON, hdr_rect)
            pygame.draw.line(screen, CLR_PANEL_BORDER, (0, 50), (WIDTH, 50), 2)

            team_a_rect = pygame.Rect(20, 10, 100, 32)
            pygame.draw.rect(screen, CLR_CRIMSON_MUTED if force_selector.active_team == "Team A" else (22, 10, 14), team_a_rect)
            screen.blit(font_big.render("Team A", True, (255, 255, 230)), (35, 16))

            team_b_rect = pygame.Rect(130, 10, 100, 32)
            pygame.draw.rect(screen, CLR_CRIMSON_MUTED if force_selector.active_team == "Team B" else (22, 10, 14), team_b_rect)
            screen.blit(font_big.render("Team B", True, (200, 200, 200)), (145, 16))

            b_str = f"BUDGET: {force_selector.budget_req} RP / {force_selector.budget_rar} RarP    |    SPENT: {force_selector.spent_req} RP / {force_selector.spent_rar} RarP    |    REMAIN: {force_selector.remain_req} RP / {force_selector.remain_rar} RarP"
            screen.blit(font_normal.render(b_str, True, CLR_TEXT_GOLD), (280, 16))

            nat_panel = pygame.Rect(15, 65, 350, 660)
            pygame.draw.rect(screen, (22, 12, 16), nat_panel)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, nat_panel, 1)
            screen.blit(font_big.render("Nation", True, (230, 200, 205)), (25, 78))

            for i, nat in enumerate(force_selector.nations):
                bx = 25 + (i % 2) * 165
                by = 110 + (i // 2) * 40
                n_rect = pygame.Rect(bx, by, 155, 32)
                is_sel = (force_selector.selected_nation == nat)
                pygame.draw.rect(screen, CLR_CRIMSON_MUTED if is_sel else (32, 14, 18), n_rect)
                pygame.draw.rect(screen, CLR_CRIMSON_BRIGHT if is_sel else CLR_PANEL_BORDER, n_rect, 1)
                screen.blit(font_subscript.render(nat, True, (255, 255, 255) if is_sel else CLR_TEXT_MUTED), (bx + 8, by + 8))

            cat_panel = pygame.Rect(375, 65, 890, 45)
            pygame.draw.rect(screen, (22, 12, 16), cat_panel)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, cat_panel, 1)
            for j, cat in enumerate(force_selector.categories):
                cbx = 385 + j * 175
                c_rect = pygame.Rect(cbx, 72, 165, 32)
                is_c_sel = (force_selector.selected_category == cat)
                pygame.draw.rect(screen, CLR_CRIMSON_MUTED if is_c_sel else (32, 14, 18), c_rect)
                pygame.draw.rect(screen, CLR_CRIMSON_BRIGHT if is_c_sel else CLR_PANEL_BORDER, c_rect, 1)
                screen.blit(font_normal.render(cat, True, (255, 255, 255) if is_c_sel else CLR_TEXT_MUTED), (cbx + 14, 78))

            items_panel = pygame.Rect(375, 120, 540, 605)
            pygame.draw.rect(screen, (18, 10, 14), items_panel)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, items_panel, 1)
            screen.blit(font_big.render(f"CATALOG: {force_selector.selected_category.upper()}", True, (240, 210, 215)), (385, 130))

            cat_items = force_selector.catalog.get(force_selector.selected_category, [])
            for k, itm in enumerate(cat_items):
                ir = pygame.Rect(385, 160 + k * 52, 520, 44)
                pygame.draw.rect(screen, (28, 13, 18), ir)
                pygame.draw.rect(screen, CLR_PANEL_BORDER, ir, 1)
                screen.blit(font_big.render(itm["name"], True, CLR_TEXT_LIGHT), (395, 165 + k * 52))
                pts_txt = f"Req: {itm['req']} RP  |  Rar: {itm['rar']} RarP"
                screen.blit(font_subscript.render(pts_txt, True, CLR_TEXT_GOLD), (395, 184 + k * 52))

                sub_txt = " + ".join(itm.get("subordinates", itm.get("loadout", [itm.get("desc", "")]))[:2])
                if sub_txt:
                    screen.blit(font_subscript.render(f"({sub_txt})", True, CLR_TEXT_MUTED), (620, 172 + k * 52))

                add_lbl = font_subscript.render("[+ Request]", True, CLR_ACCENT_RED)
                screen.blit(add_lbl, (830, 175 + k * 52))

            roster_panel = pygame.Rect(925, 120, 340, 605)
            pygame.draw.rect(screen, (18, 10, 14), roster_panel)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, roster_panel, 1)
            screen.blit(font_big.render("Active Units", True, (240, 210, 215)), (935, 130))

            if not force_selector.purchased_units:
                screen.blit(font_normal.render("No reinforcements acquired.", True, CLR_TEXT_MUTED), (940, 170))
            else:
                for idx, p_item in enumerate(force_selector.purchased_units):
                    pr_box = pygame.Rect(935, 160 + idx * 36, 320, 30)
                    pygame.draw.rect(screen, (30, 14, 19), pr_box)
                    screen.blit(font_subscript.render(f"{p_item['name']}", True, CLR_TEXT_LIGHT), (942, 168 + idx * 36))
                    screen.blit(font_subscript.render(f"{p_item['req']} RP", True, CLR_TEXT_GOLD), (1150, 168 + idx * 36))
                    del_lbl = font_subscript.render("[X]", True, CLR_CRIMSON_BRIGHT)
                    screen.blit(del_lbl, (1235, 168 + idx * 36))

            b_btn = pygame.Rect(20, HEIGHT - 55, 140, 42)
            pygame.draw.rect(screen, (35, 15, 20), b_btn)
            screen.blit(font_big.render("<< Back to Briefing", True, CLR_TEXT_LIGHT), (35, HEIGHT - 42))

            deploy_btn = pygame.Rect(WIDTH - 240, HEIGHT - 55, 220, 42)
            pygame.draw.rect(screen, (90, 18, 28), deploy_btn)
            pygame.draw.rect(screen, CLR_CRIMSON_BRIGHT, deploy_btn, 2)
            screen.blit(font_big.render("Start Level >>", True, (255, 240, 240)), (WIDTH - 225, HEIGHT - 42))
# help screen for dummies
        elif game_state == "HELP":
            panel = pygame.Rect(180, 50, WIDTH - 360, HEIGHT - 120)
            pygame.draw.rect(screen, CLR_PANEL_CRIMSON, panel)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, panel, 2)

            help_lines = [
                ("Part 1: Basic Controls", True),
                ("1. Selecting Units: Left-click any soldier or vehicle. Entire squad selects at once.", False),
                ("2. Squad Movement: Left-click grid in ORDER phase to plot paths.", False),
                ("3. Deselect: Right-click anywhere in map space to drop current squad selection.", False),
                ("4. Orders & Stances: [N] Normal, [Q] Quick, [F] Fast, [S] Sneak, [A] Assault, [H] Halt.", False),
                ("5. Turns: Give orders in ORDER phase, press [SPACE] or START ACTION for 30s ACTION phase.", False),
                (r"6. Press \ to debug", False), # removing this in the real game
                ("7. Camera Pan: Use Arrow Keys [UP/DOWN/LEFT/RIGHT] to shift map view.", False),
            ]
            y_offset = 80
            for line, is_header in help_lines:
                fnt = font_big if is_header else font_normal
                clr = CLR_TEXT_GOLD if is_header else CLR_TEXT_LIGHT
                txt_surf = fnt.render(line, True, clr)
                screen.blit(txt_surf, (215, y_offset))
                y_offset += 34

            back_btn.draw(screen, font_big, font_subscript)

        elif game_state == "GAME":
            cam_offset = (int(camera_x), int(camera_y))
            tactical_grid.draw(screen, cam_offset)

            for c_marker in casualties_group:
                c_marker.draw(screen, cam_offset)

            for t in all_teams:
                t.draw(screen, cam_offset, debug_mode=debug_mode)

            for p in projectiles_group:
                screen.blit(p.image, p.rect.move(-cam_offset[0], -cam_offset[1]))
            for b in buildings_group:
                screen.blit(b.image, b.rect.move(-cam_offset[0], -cam_offset[1]))
            # [ADD] Draw muzzle flashes and explosions with camera offset
            for fx in effects_group:
                screen.blit(fx.image, fx.rect.move(-cam_offset[0], -cam_offset[1]))

            # [ADD START] Top Turn & Phase Banner
            turn_bar = pygame.Rect(WIDTH // 2 - 220, 4, 550, 44)
            pygame.draw.rect(screen, CLR_PANEL_CRIMSON, turn_bar, border_radius=4)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, turn_bar, 2, border_radius=4)
            if turn_phase == "ORDER":
                phase_txt = font_header.render(f"TURN {turn_number}  |  ORDER PHASE", True, CLR_TEXT_GOLD)
                screen.blit(phase_txt, (turn_bar.x + 16, turn_bar.y + 10))
                end_orders_btn.draw(screen, font_normal, font_subscript)
            else:
                secs_left = action_ticks_remaining / 60.0
                phase_txt = font_header.render(f"TURN {turn_number}  |  ACTION PHASE: {secs_left:04.1f}s", True, CLR_ACCENT_RED)
                screen.blit(phase_txt, phase_txt.get_rect(center=turn_bar.center))
            # [ADD END]

            #UI Panels
            console_rect = pygame.Rect(0, 640, WIDTH, 160)
            pygame.draw.rect(screen, CLR_PANEL_CRIMSON, console_rect)
            pygame.draw.line(screen, CLR_PANEL_BORDER, (0, 640), (WIDTH, 640), 2)

            #  sqsuad information
            panel_left = pygame.Rect(8, 646, 350, 146)
            pygame.draw.rect(screen, (20, 10, 14), panel_left)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, panel_left, 1)

            if selected_squad:
                lead = selected_squad.leader
                lead_ft = selected_squad.fireteams[0] if selected_squad.fireteams else None
                squad_side = lead_ft.team if lead_ft else "blue"
                team_clr = (130, 180, 255) if squad_side == "blue" else (255, 90, 90)

                # [EDIT START] Display either Vehicle info (ammo/optics/HP) or Infantry Squad info (+ Binoculars tag)
                if isinstance(lead_ft, Vehicle):
                    name_lbl = font_big.render(f"Vehicle: {lead_ft.unit_name} [{lead_ft.current_ammo}]", True, team_clr)
                    c2_lbl = font_subscript.render(f"Rangefinder + Scopes | {lead_ft.weapon_name}", True, CLR_TEXT_GOLD)
                    eff_txt = font_normal.render(f"Hull Integrity: {lead_ft.hp} / {lead_ft.max_hp} HP", True, CLR_TEXT_LIGHT)
                else:
                    has_bino = any(hasattr(ft, "has_binoculars") and ft.has_binoculars() for ft in selected_squad.fireteams)
                    bino_str = " | [BINOCULARS]" if has_bino else ""
                    name_lbl = font_big.render(f"Squad: {lead.name} [HQ]", True, team_clr)
                    c2_lbl = font_subscript.render(f"Voice, visual radio{bino_str}", True, CLR_TEXT_GOLD)
                    tot_members = sum(getattr(ft, "initial_member_count", len(ft.members)) for ft in selected_squad.fireteams)
                    alive_members = sum(len(ft.members) for ft in selected_squad.fireteams)
                    eff_txt = font_normal.render(f"Effectiveness: {alive_members} / {tot_members} Squadmembers", True, CLR_TEXT_LIGHT)

                screen.blit(name_lbl, (20, 656))
                screen.blit(c2_lbl, (20, 676))
                screen.blit(eff_txt, (20, 698))
                # [EDIT END]

                avg_supp = sum(ft.suppression for ft in selected_squad.fireteams) / max(1, len(selected_squad.fireteams))
                supp_pct = min(1.0, avg_supp / 100.0)

                supp_bar = pygame.Rect(20, 726, 180, 16)
                pygame.draw.rect(screen, (15, 8, 10), supp_bar)
                fill_w = int(180 * supp_pct)
                if fill_w > 0:
                    pygame.draw.rect(screen, (220, 40, 50), (20, 726, fill_w, 16))
                pygame.draw.rect(screen, CLR_PANEL_BORDER, supp_bar, 1)

                supp_lbl = font_subscript.render(f"Suppression: {int(avg_supp)}%", True, CLR_TEXT_MUTED)
                screen.blit(supp_lbl, (20, 746))
            else:
                lbl_none = font_normal.render("None selected", True, CLR_TEXT_MUTED)
                screen.blit(lbl_none, (20, 665))
                sub_none = font_subscript.render("Left-click any soldier or vehicle to select", True, CLR_TEXT_MUTED)
                screen.blit(sub_none, (20, 695))

            # Center Panel: Individual Soldiers Roster
            panel_center = pygame.Rect(366, 646, 530, 146)
            pygame.draw.rect(screen, (20, 10, 14), panel_center)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, panel_center, 1)

            spawn_blue_btn.draw(screen, font_normal, font_subscript)
            spawn_red_btn.draw(screen, font_normal, font_subscript)

            if selected_squad:
                y_sol = 678
                for ft in selected_squad.fireteams:
                    for s in ft.members:
                        if y_sol > 770:
                            break
                        cond_clr = (140, 230, 140) if s.condition > 150 else ((240, 180, 50) if s.condition > 50 else (230, 60, 60))
                        cond_str = "Fine" if s.condition > 150 else ("Wounded" if s.condition > 50 else "KIA")
                        bino_tag = " [BINO]" if getattr(s, "binoculars", None) else ""  # [ADD]
                        s_line = f"{s.rank} {s.name} - {s.weapon}{bino_tag}"
                        screen.blit(font_subscript.render(s_line, True, CLR_TEXT_LIGHT), (376, y_sol))
                        screen.blit(font_subscript.render(f"[{cond_str}]", True, cond_clr), (700, y_sol))
                        y_sol += 18

            # Right Panel: Orders
            panel_right = pygame.Rect(904, 646, 368, 146)
            pygame.draw.rect(screen, (20, 10, 14), panel_right)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, panel_right, 1)

            tab_mov = pygame.Rect(910, 648, 110, 20)
            pygame.draw.rect(screen, CLR_CRIMSON_MUTED if current_ui_tab == "MOVEMENT" else (28, 12, 16), tab_mov)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, tab_mov, 1)
            screen.blit(font_big.render("MOVEMENT", True, CLR_TEXT_LIGHT if current_ui_tab == "MOVEMENT" else CLR_TEXT_MUTED), (922, 650))

            tab_com = pygame.Rect(1025, 648, 110, 20)
            pygame.draw.rect(screen, CLR_CRIMSON_MUTED if current_ui_tab == "COMBAT" else (28, 12, 16), tab_com)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, tab_com, 1)
            screen.blit(font_big.render("COMBAT", True, CLR_TEXT_LIGHT if current_ui_tab == "COMBAT" else CLR_TEXT_MUTED), (1045, 650))

            tab_spc = pygame.Rect(1140, 648, 110, 20)
            pygame.draw.rect(screen, CLR_CRIMSON_MUTED if current_ui_tab == "SPECIAL" else (28, 12, 16), tab_spc)
            pygame.draw.rect(screen, CLR_PANEL_BORDER, tab_spc, 1)
            screen.blit(font_big.render("SPECIAL", True, CLR_TEXT_LIGHT if current_ui_tab == "SPECIAL" else CLR_TEXT_MUTED), (1155, 650))

            active_buttons = movement_order_buttons if current_ui_tab == "MOVEMENT" else (combat_order_buttons if current_ui_tab == "COMBAT" else special_order_buttons)
            lead_ft = selected_squad.fireteams[0] if (selected_squad and selected_squad.fireteams) else None
            for btn in active_buttons:
                btn_order_map = {
                    "MOVE": "Normal", "QUICK": "Quick", "FAST": "Fast",
                    "SNEAK": "Sneak", "ASSAULT": "Assault", "HALT": "Halt",
                    "MOUNT": "Mount", "DISMOUNT": "Dismount"
                }
                btn.active = bool(lead_ft and lead_ft.move_order == btn_order_map.get(btn.title))
                btn.draw(screen, font_normal, font_subscript)
# debug for testing
        if debug_mode:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 185))
            screen.blit(overlay, (0, 0))

            test_hdr = font_debug.render("Testing mode", True, CLR_ACCENT_RED)
            screen.blit(test_hdr, test_hdr.get_rect(center=(WIDTH // 2, 60)))

            wx = int(mpos[0] + camera_x)
            wy = int(mpos[1] + camera_y)
            cgx, cgy = tactical_grid.world_to_grid(wx, wy)
            coord_str = f"WORLD X: {wx}  Y: {wy}  (CAM: {int(camera_x)}, {int(camera_y)})"
            grid_str = f"GRID CELL: [Col: {cgx}, Row: {cgy}]"

            coord_surf = font_debug.render(coord_str, True, (255, 255, 255))
            grid_surf = font_header.render(grid_str, True, CLR_TEXT_GOLD)

            screen.blit(coord_surf, coord_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            screen.blit(grid_surf, grid_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 35)))

            hint_surf = font_subscript.render(r"Press [ \ ] again to exit debug mode", True, (190, 190, 190))
            screen.blit(hint_surf, hint_surf.get_rect(center=(WIDTH // 2, HEIGHT - 60)))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:

        pygame.quit()


# ui/button.py - Dark Crimson & Obsidian tactical interface button component
import pygame

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

        # Dark Crimson & Obsidian Theme Palette
        if self.active:
            # Active selected order / button
            base_color = (95, 20, 28)
            border_light = (235, 60, 75)
            border_dark = (40, 8, 12)
            text_color = (255, 245, 230)
            hk_color = (245, 200, 110)
        elif hovered:
            # Hover highlight
            base_color = (48, 18, 24)
            border_light = (175, 45, 58)
            border_dark = (20, 6, 9)
            text_color = (255, 255, 255)
            hk_color = (230, 190, 130)
        else:
            # Neutral state
            base_color = (26, 12, 16)
            border_light = (85, 24, 32)
            border_dark = (14, 5, 8)
            text_color = (225, 218, 220)
            hk_color = (150, 125, 130)

        # Beveled tactical panel button
        pygame.draw.rect(surface, base_color, self.rect)
        pygame.draw.line(surface, border_light, self.rect.topleft, self.rect.topright, 2)
        pygame.draw.line(surface, border_light, self.rect.topleft, self.rect.bottomleft, 2)
        pygame.draw.line(surface, border_dark, self.rect.bottomleft, self.rect.bottomright, 2)
        pygame.draw.line(surface, border_dark, self.rect.topright, self.rect.bottomright, 2)

        txt_surf = font_main.render(self.title, True, text_color)
        surface.blit(txt_surf, txt_surf.get_rect(center=(self.rect.centerx, self.rect.centery - (2 if self.hotkey else 0))))

        if self.hotkey:
            hk_surf = font_sub.render(f"[{self.hotkey}]", True, hk_color)
            surface.blit(hk_surf, (self.rect.right - hk_surf.get_width() - 5, self.rect.bottom - hk_surf.get_height() - 3))

    def handle_click(self, mpos):
        if self.rect.collidepoint(mpos) and self.callback:
            self.callback()
            return True
        return False
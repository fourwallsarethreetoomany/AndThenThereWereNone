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

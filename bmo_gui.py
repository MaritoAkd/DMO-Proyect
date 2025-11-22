import pygame
import os
import threading
import time

pygame.init()

INFO_PANTALLA = pygame.display.Info()
ANCHO_PANTALLA = INFO_PANTALLA.current_w
ALTO_PANTALLA = INFO_PANTALLA.current_h

VENTANA = pygame.display.set_mode((ANCHO_PANTALLA, ALTO_PANTALLA), pygame.FULLSCREEN)
pygame.display.set_caption("BMO - La Interfaz")

COLOR_MENU_BG = (40, 40, 40, 200)
COLOR_TEXTO = (240, 240, 240)
COLOR_HOVER = (255, 255, 255, 70)
BORDE_RADIO = 15
MENU_WIDTH = int(ANCHO_PANTALLA * 0.25)
MENU_HEIGHT = int(ALTO_PANTALLA * 0.5)
MENU_OPTIONS = ["Apariencia", "Juegos", "Para profesionales", "FAQ/Contacto"]
FONT_MENU = pygame.font.SysFont("Arial", 28, bold=True)
FONT_MENU_ITEM = pygame.font.SysFont("Arial", 24)
FONT_AP_TITLE = pygame.font.SysFont("Arial", 32, bold=True)
FONT_AP_LABEL = pygame.font.SysFont("Arial", 20)
IMG_SIZE_BASE_PX = 60
IMG_SIZE_SELECTED_PX = 75
COLOR_SELECTION_OUTLINE = (255, 255, 255)

class HamburgerMenu:
    def __init__(self):
        self.is_open = False
        self.target_x = -MENU_WIDTH
        self.current_x = -MENU_WIDTH
        self.button_rect = pygame.Rect(20, 20, 50, 40)
        self.menu_rect = pygame.Rect(0, 0, MENU_WIDTH, MENU_HEIGHT)
        self.menu_rect.center = (MENU_WIDTH // 2, int(ALTO_PANTALLA * 0.45))
        self.menu_rect.left = self.current_x
        self.option_rects = []
        self.hovered_index = -1
        self._calculate_option_rects()

    def _calculate_option_rects(self):
        self.option_rects = []
        start_y = self.menu_rect.top + 100
        padding = 15
        for i, option in enumerate(MENU_OPTIONS):
            text_surf = FONT_MENU_ITEM.render(option, True, COLOR_TEXTO)
            item_height = text_surf.get_height() + padding
            rect = pygame.Rect(self.menu_rect.left + padding, 
                               start_y + i * item_height,
                               MENU_WIDTH - 2 * padding, 
                               item_height)
            self.option_rects.append(rect)

    def toggle(self):
        self.is_open = not self.is_open
        self.target_x = 0 if self.is_open else -MENU_WIDTH
        self._calculate_option_rects() 

    def update(self, dt):
        speed = 8.0
        self.current_x += (self.target_x - self.current_x) * speed * dt
        self.menu_rect.left = int(self.current_x)
        padding = 15
        start_y = self.menu_rect.top + 100 
        for i, rect in enumerate(self.option_rects):
             text_surf = FONT_MENU_ITEM.render(MENU_OPTIONS[i], True, COLOR_TEXTO)
             item_height = text_surf.get_height() + padding
             rect.left = self.menu_rect.left + padding
             rect.top = start_y + i * item_height

    def check_hover(self, mouse_pos):
        self.hovered_index = -1
        if self.is_open and self.menu_rect.collidepoint(mouse_pos):
             for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(mouse_pos):
                    self.hovered_index = i
                    break
        return self.hovered_index

    def check_click(self, mouse_pos):
        if self.button_rect.collidepoint(mouse_pos):
            self.toggle()
            return "TOGGLE"
        if self.is_open and self.menu_rect.collidepoint(mouse_pos):
            close_rect = pygame.Rect(self.menu_rect.right - 35, self.menu_rect.top + 15, 20, 20)
            if close_rect.collidepoint(mouse_pos):
                self.toggle()
                return "TOGGLE"
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(mouse_pos):
                    self.toggle()
                    return MENU_OPTIONS[i]
        return None

    def draw(self, surface):
        color_button = (0, 0, 0)
        bar_height = 4
        bar_width = 30
        gap = 7
        x_start = self.button_rect.centerx - bar_width // 2
        for i in range(3):
            y_start = self.button_rect.centery - gap - bar_height + i * (gap + bar_height)
            pygame.draw.rect(surface, color_button, (x_start, y_start, bar_width, bar_height), border_radius=2) 
        if self.current_x > -MENU_WIDTH + 5: 
            menu_surface = pygame.Surface((MENU_WIDTH, MENU_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(menu_surface, COLOR_MENU_BG, (0, 0, MENU_WIDTH, MENU_HEIGHT), border_radius=BORDE_RADIO)
            pygame.draw.rect(menu_surface, (100, 100, 100), (0, 0, MENU_WIDTH, MENU_HEIGHT), width=1, border_radius=BORDE_RADIO)
            close_rect_rel = pygame.Rect(MENU_WIDTH - 35, 15, 20, 20) 
            pygame.draw.line(menu_surface, COLOR_TEXTO, close_rect_rel.topleft, close_rect_rel.bottomright, 3)
            pygame.draw.line(menu_surface, COLOR_TEXTO, close_rect_rel.topright, close_rect_rel.bottomleft, 3)
            padding = 15
            for i, option in enumerate(MENU_OPTIONS):
                rect = self.option_rects[i].copy()
                if i == self.hovered_index:
                    hover_rect_rel = pygame.Rect(padding, rect.top - self.menu_rect.top, rect.width, rect.height)
                    hover_surface = pygame.Surface((hover_rect_rel.width, hover_rect_rel.height), pygame.SRCALPHA)
                    pygame.draw.rect(hover_surface, COLOR_HOVER, (0, 0, hover_rect_rel.width, hover_rect_rel.height), border_radius=5)
                    menu_surface.blit(hover_surface, hover_rect_rel.topleft)
                text_surf = FONT_MENU_ITEM.render(option, True, COLOR_TEXTO)
                text_x_rel = padding + 5
                text_y_rel = rect.top - self.menu_rect.top + (rect.height - text_surf.get_height()) // 2 
                menu_surface.blit(text_surf, (text_x_rel, text_y_rel))
            surface.blit(menu_surface, self.menu_rect.topleft)

class AppearanceMenu:
    def __init__(self):
        self.skins_list = list(IMAGENES_BMO_SKIN.keys())
        self.current_skin_index = 0
        self.menu_center_rel = (0.5, 0.5) 
        self.menu_size_rel = (0.7, 0.7)  
        self.title_pos_rel = (0.1, 0.05)
        self.label_pos_rel = (0.1, 0.2)
        self.carousel_center_rel = (0.5, 0.5)
        self.back_button_pos_rel = (0.5, 0.9)
        self.arrow_left_rect = None
        self.arrow_right_rect = None
        self.back_button_rect = None

    def get_relative_pos(self, base_rect, rel_pos):
        x = base_rect.left + base_rect.width * rel_pos[0]
        y = base_rect.top + base_rect.height * rel_pos[1]
        return int(x), int(y)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.arrow_left_rect and self.arrow_left_rect.collidepoint(event.pos):
                self.current_skin_index = (self.current_skin_index - 1 + len(self.skins_list)) % len(self.skins_list)
                return self.skins_list[self.current_skin_index]
            if self.arrow_right_rect and self.arrow_right_rect.collidepoint(event.pos):
                self.current_skin_index = (self.current_skin_index + 1) % len(self.skins_list)
                return self.skins_list[self.current_skin_index]
            if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                return "BACK"
        return None

    def draw(self, surface, base_rect):
        menu_width = int(base_rect.width * self.menu_size_rel[0])
        menu_height = int(base_rect.height * self.menu_size_rel[1])
        center_x_abs, center_y_abs = self.get_relative_pos(base_rect, self.menu_center_rel)
        menu_x = center_x_abs - menu_width // 2
        menu_y = center_y_abs - menu_height // 2
        menu_rect_abs = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        pygame.draw.rect(menu_surface, COLOR_MENU_BG, (0, 0, menu_width, menu_height), border_radius=BORDE_RADIO)
        title_surf = FONT_AP_TITLE.render("Apariencia", True, COLOR_TEXTO)
        title_x = menu_width * self.title_pos_rel[0]
        title_y = menu_height * self.title_pos_rel[1]
        menu_surface.blit(title_surf, (title_x, title_y))
        label_surf = FONT_AP_LABEL.render("Color de DMO:", True, COLOR_TEXTO)
        label_x = menu_width * self.label_pos_rel[0]
        label_y = menu_height * self.label_pos_rel[1]
        menu_surface.blit(label_surf, (label_x, label_y))
        skins = self.skins_list
        num_skins = len(skins)
        center_index = self.current_skin_index
        left_index = (center_index - 1 + num_skins) % num_skins
        right_index = (center_index + 1) % num_skins
        carousel_center_x = menu_width * self.carousel_center_rel[0]
        carousel_center_y = menu_height * self.carousel_center_rel[1]
        image_data = [(skins[left_index], IMG_SIZE_BASE_PX, -100), 
                      (skins[center_index], IMG_SIZE_SELECTED_PX, 0),
                      (skins[right_index], IMG_SIZE_BASE_PX, 100)]
        for skin_key, img_size_px, offset_x in image_data:
            img_original = IMAGENES_BMO_SKIN[skin_key]
            img_scale = min(img_size_px / img_original.get_width(), img_size_px / img_original.get_height())
            scaled_img = pygame.transform.smoothscale(img_original, (int(img_original.get_width() * img_scale), int(img_original.get_height() * img_scale)))
            img_rect = scaled_img.get_rect(center=(carousel_center_x + offset_x, carousel_center_y))
            if skin_key == skins[center_index]:
                outline_rect = img_rect.inflate(6, 6)
                pygame.draw.rect(menu_surface, COLOR_SELECTION_OUTLINE, outline_rect, 3, border_radius=5)
            menu_surface.blit(scaled_img, img_rect)
        arrow_size = 20
        arrow_y_rel = carousel_center_y
        arrow_left_x_rel = carousel_center_x - 170
        self.arrow_left_rect = pygame.Rect(menu_rect_abs.left + arrow_left_x_rel - arrow_size//2, 
                                           menu_rect_abs.top + arrow_y_rel - arrow_size//2, 
                                           arrow_size, arrow_size)
        pygame.draw.polygon(menu_surface, COLOR_TEXTO, [(arrow_left_x_rel - 5, arrow_y_rel), 
                                                        (arrow_left_x_rel + 5, arrow_y_rel - 10), 
                                                        (arrow_left_x_rel + 5, arrow_y_rel + 10)])
        arrow_right_x_rel = carousel_center_x + 170
        self.arrow_right_rect = pygame.Rect(menu_rect_abs.left + arrow_right_x_rel - arrow_size//2, 
                                            menu_rect_abs.top + arrow_y_rel - arrow_size//2, 
                                            arrow_size, arrow_size)
        pygame.draw.polygon(menu_surface, COLOR_TEXTO, [(arrow_right_x_rel + 5, arrow_y_rel), 
                                                        (arrow_right_x_rel - 5, arrow_y_rel - 10), 
                                                        (arrow_right_x_rel - 5, arrow_y_rel + 10)])
        back_surf = FONT_AP_LABEL.render("[ VOLVER ]", True, COLOR_TEXTO)
        back_pos_x = menu_width * self.back_button_pos_rel[0]
        back_pos_y = menu_height * self.back_button_pos_rel[1]
        back_rect_rel = back_surf.get_rect(center=(back_pos_x, back_pos_y))
        menu_surface.blit(back_surf, back_rect_rel)
        self.back_button_rect = back_rect_rel.move(menu_rect_abs.topleft)
        surface.blit(menu_surface, menu_rect_abs.topleft)

class ProfessionalMenu:
    def __init__(self):
        self.menu_center_rel = (0.5, 0.5) 
        self.menu_size_rel = (0.7, 0.7)
        self.options = ["Cerebro DMO (Historial)", "Notas del Profesional", "Personalidad del Usuario"]
        self.option_rects = []
        self.hovered_index = -1
        self.menu_rect_abs = None
        self.title_pos_rel = (0.1, 0.05)
        self.back_button_pos_rel = (0.5, 0.9)
        self.back_button_rect = None

    def get_relative_pos(self, base_rect, rel_pos):
        x = base_rect.left + base_rect.width * rel_pos[0]
        y = base_rect.top + base_rect.height * rel_pos[1]
        return int(x), int(y)

    def _calculate_option_rects(self):
        if not self.menu_rect_abs: return
        self.option_rects = []
        start_y = self.menu_rect_abs.height * 0.2
        padding_y = 15
        padding_x = 20
        for i, option in enumerate(self.options):
            text_surf = FONT_AP_LABEL.render(option, True, COLOR_TEXTO)
            item_height = text_surf.get_height() + padding_y
            rect = pygame.Rect(self.menu_rect_abs.left + padding_x, 
                               self.menu_rect_abs.top + start_y + i * item_height,
                               self.menu_rect_abs.width - 2 * padding_x, 
                               item_height)
            self.option_rects.append(rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.back_button_rect and self.back_button_rect.collidepoint(mouse_pos):
                return "BACK"
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(mouse_pos):
                    return self.options[i]
        return None

    def check_hover(self, mouse_pos):
        self.hovered_index = -1
        for i, rect in enumerate(self.option_rects):
            if rect.collidepoint(mouse_pos):
                self.hovered_index = i
                break
        return self.hovered_index

    def draw(self, surface, base_rect):
        menu_width = int(base_rect.width * self.menu_size_rel[0])
        menu_height = int(base_rect.height * self.menu_size_rel[1])
        center_x_abs, center_y_abs = self.get_relative_pos(base_rect, self.menu_center_rel)
        menu_x = center_x_abs - menu_width // 2
        menu_y = center_y_abs - menu_height // 2
        self.menu_rect_abs = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        self._calculate_option_rects()
        menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        pygame.draw.rect(menu_surface, COLOR_MENU_BG, (0, 0, menu_width, menu_height), border_radius=BORDE_RADIO)
        title_surf = FONT_AP_TITLE.render("Para Profesionales", True, COLOR_TEXTO)
        title_x = menu_width * self.title_pos_rel[0]
        title_y = menu_height * self.title_pos_rel[1]
        menu_surface.blit(title_surf, (title_x, title_y))
        for i, option in enumerate(self.options):
            rect_abs = self.option_rects[i]
            rect_rel = rect_abs.move(-self.menu_rect_abs.left, -self.menu_rect_abs.top) 
            if i == self.hovered_index:
                hover_surface = pygame.Surface((rect_rel.width, rect_rel.height), pygame.SRCALPHA)
                pygame.draw.rect(hover_surface, COLOR_HOVER, (0, 0, rect_rel.width, rect_rel.height), border_radius=5)
                menu_surface.blit(hover_surface, rect_rel.topleft)
            text_surf = FONT_AP_LABEL.render(option, True, COLOR_TEXTO)
            text_x_rel = rect_rel.left + 5
            text_y_rel = rect_rel.top + (rect_rel.height - text_surf.get_height()) // 2
            menu_surface.blit(text_surf, (text_x_rel, text_y_rel))
        back_surf = FONT_AP_LABEL.render("[ VOLVER ]", True, COLOR_TEXTO)
        back_pos_x = menu_width * self.back_button_pos_rel[0]
        back_pos_y = menu_height * self.back_button_pos_rel[1]
        back_rect_rel = back_surf.get_rect(center=(back_pos_x, back_pos_y))
        menu_surface.blit(back_surf, back_rect_rel)
        self.back_button_rect = back_rect_rel.move(self.menu_rect_abs.topleft)
        surface.blit(menu_surface, self.menu_rect_abs.topleft)

IMAGENES_OJOS = {}
IMAGENES_BOCAS = {}
IMAGENES_BMO_SKIN = {}
imagen_base_bmo = None
directorio_base = os.path.dirname(__file__)

def cargar_imagenes():
    global IMAGENES_OJOS, IMAGENES_BOCAS, imagen_base_bmo, IMAGENES_BMO_SKIN
    ruta_base_bmo = os.path.join(directorio_base, "recursos", "BMO_faces")
    try:
        ruta_blank_original = os.path.join(ruta_base_bmo, "blank.png")
        imagen_default = pygame.image.load(ruta_blank_original).convert_alpha()
        IMAGENES_BMO_SKIN["blank"] = imagen_default
    except:
        imagen_default = pygame.Surface((100, 100))
        imagen_default.fill((100, 100, 100))
        IMAGENES_BMO_SKIN["blank"] = imagen_default
    imagen_base_bmo = IMAGENES_BMO_SKIN["blank"]
    for i in range(1, 6):
        skin_name = f"blank{i}"
        try:
            ruta_skin = os.path.join(ruta_base_bmo, f"{skin_name}.png")
            IMAGENES_BMO_SKIN[skin_name] = pygame.image.load(ruta_skin).convert_alpha()
        except:
            IMAGENES_BMO_SKIN[skin_name] = imagen_default
    ruta_ojos = os.path.join(directorio_base, "recursos", "BMO_faces", "Eyes")
    try:
        for filename in os.listdir(ruta_ojos):
            if filename.endswith(".png"):
                key = filename.replace("Ojos_", "").replace(".png", "")
                path = os.path.join(ruta_ojos, filename)
                IMAGENES_OJOS[key] = pygame.image.load(path).convert_alpha()
    except:
        IMAGENES_OJOS["idle"] = pygame.Surface((20, 10))
        IMAGENES_OJOS["idle"].fill((255, 255, 255))
    ruta_bocas = os.path.join(directorio_base, "recursos", "BMO_faces", "Mouth")
    try:
        for filename in os.listdir(ruta_bocas):
            if filename.endswith(".png"):
                key = filename.replace("Boca_", "").replace(".png", "")
                path = os.path.join(ruta_bocas, filename)
                IMAGENES_BOCAS[key] = pygame.image.load(path).convert_alpha()
    except:
        IMAGENES_BOCAS["Idle"] = pygame.Surface((20, 5))
        IMAGENES_BOCAS["Idle"].fill((255, 255, 255))

cargar_imagenes()

current_eye_key = "idle"
current_mouth_key = "Idle"
is_speaking = False
CENTRO_OJOS_RELATIVO = (0.5, 0.39)
CENTRO_BOCA_RELATIVO = (0.5, 0.69)

def get_absolute_position(image_to_place, base_rect, relative_center_coords):
    center_x_abs = base_rect.left + base_rect.width * relative_center_coords[0]
    center_y_abs = base_rect.top + base_rect.height * relative_center_coords[1]
    return int(center_x_abs - image_to_place.get_width() // 2), int(center_y_abs - image_to_place.get_height() // 2)

def set_active_skin(skin_key):
    global imagen_base_bmo
    if skin_key in IMAGENES_BMO_SKIN:
        imagen_base_bmo = IMAGENES_BMO_SKIN[skin_key]

def draw_bmo(state, eye_key, mouth_key, talking_frame, displayed_text="", menu=None, app_state="BMO_FACE", appearance_menu=None, professional_menu=None):
    global is_speaking, current_mouth_key
    VENTANA.fill((0, 0, 0))
    base_width, base_height = imagen_base_bmo.get_size()
    scale = min(ANCHO_PANTALLA / base_width, ALTO_PANTALLA / base_height)
    new_width = int(base_width * scale)
    new_height = int(base_height * scale)
    scaled_base = pygame.transform.smoothscale(imagen_base_bmo, (new_width, new_height))
    base_rect = scaled_base.get_rect(center=VENTANA.get_rect().center)
    VENTANA.blit(scaled_base, base_rect)
    if app_state == "BMO_FACE":
        eye_img = IMAGENES_OJOS.get(eye_key, IMAGENES_OJOS["idle"])
        # Si is_speaking, escoger una boca de talking basada en talking_frame (1..4)
        if is_speaking:
            talking_key = f"talking_{talking_frame}"
            mouth_img = IMAGENES_BOCAS.get(talking_key, IMAGENES_BOCAS.get(current_mouth_key, IMAGENES_BOCAS["Idle"]))
        else:
            mouth_img = IMAGENES_BOCAS.get(current_mouth_key if not is_speaking else mouth_key, IMAGENES_BOCAS["Idle"])
        scaled_eye = pygame.transform.smoothscale(eye_img, (int(eye_img.get_width() * scale), int(eye_img.get_height() * scale)))
        scaled_mouth = pygame.transform.smoothscale(mouth_img, (int(mouth_img.get_width() * scale), int(mouth_img.get_height() * scale)))
        pos_eye = get_absolute_position(scaled_eye, base_rect, CENTRO_OJOS_RELATIVO)
        pos_mouth = get_absolute_position(scaled_mouth, base_rect, CENTRO_BOCA_RELATIVO)
        VENTANA.blit(scaled_eye, pos_eye)
        VENTANA.blit(scaled_mouth, pos_mouth)
        if displayed_text:
            text_bg_rect = pygame.Rect(0, ALTO_PANTALLA - int(80 * scale), ANCHO_PANTALLA, int(80 * scale))
            pygame.draw.rect(VENTANA, (0, 0, 0, 150), text_bg_rect)
            font_size = int(20 * scale)
            font = pygame.font.SysFont("Arial", font_size)
            text_surface = font.render(displayed_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(ANCHO_PANTALLA // 2, ALTO_PANTALLA - int(40 * scale)))
            VENTANA.blit(text_surface, text_rect)
    elif app_state == "MENU_APARIENCIA" and appearance_menu:
        appearance_menu.draw(VENTANA, base_rect)
    elif app_state == "MENU_PROFESIONAL" and professional_menu:
        professional_menu.draw(VENTANA, base_rect)
    if menu:
        menu.draw(VENTANA)
    pygame.display.flip()

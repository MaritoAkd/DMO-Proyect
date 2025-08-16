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

IMAGENES_OJOS = {}
IMAGENES_BOCAS = {}
imagen_base_bmo = None

directorio_base = os.path.dirname(__file__)

def cargar_imagenes():
    global IMAGENES_OJOS, IMAGENES_BOCAS, imagen_base_bmo

    ruta_blank = os.path.join(directorio_base, "recursos", "BMO_faces", "blank.png")
    imagen_base_bmo = pygame.image.load(ruta_blank).convert_alpha()

    ruta_ojos = os.path.join(directorio_base, "recursos", "BMO_faces", "Eyes")
    for filename in os.listdir(ruta_ojos):
        if filename.endswith(".png"):
            key = filename.replace("Ojos_", "").replace(".png", "")
            path = os.path.join(ruta_ojos, filename)
            IMAGENES_OJOS[key] = pygame.image.load(path).convert_alpha()

    ruta_bocas = os.path.join(directorio_base, "recursos", "BMO_faces", "Mouth")
    for filename in os.listdir(ruta_bocas):
        if filename.endswith(".png"):
            key = filename.replace("Boca_", "").replace(".png", "")
            path = os.path.join(ruta_bocas, filename)
            IMAGENES_BOCAS[key] = pygame.image.load(path).convert_alpha()

cargar_imagenes()

current_eye_key = "idle"
current_mouth_key = "Idle"
is_listening = False
is_speaking = False

def mouth_animation_loop():
    global current_mouth_key, is_speaking
    frame = 0
    while True:
        if is_speaking:
            frame = (frame % 4) + 1
            current_mouth_key = f"talking_{frame}"
        else:
            current_mouth_key = "Idle"
        time.sleep(0.15)

threading.Thread(target=mouth_animation_loop, daemon=True).start()

CENTRO_OJOS_RELATIVO = (0.5, 0.4)
CENTRO_BOCA_RELATIVO = (0.5, 0.7)

def get_absolute_position(image_to_place, base_rect, relative_center_coords):
    center_x_abs = base_rect.left + base_rect.width * relative_center_coords[0]
    center_y_abs = base_rect.top + base_rect.height * relative_center_coords[1]
    x = int(center_x_abs - image_to_place.get_width() // 2)
    y = int(center_y_abs - image_to_place.get_height() // 2)
    return x, y

def draw_bmo(state, eye_key, mouth_key, talking_frame, displayed_text=""):
    global is_speaking, current_mouth_key

    VENTANA.fill((0, 0, 0))

    base_width, base_height = imagen_base_bmo.get_size()
    scale = max(ANCHO_PANTALLA / base_width, ALTO_PANTALLA / base_height)
    scaled_base = pygame.transform.smoothscale(
        imagen_base_bmo,
        (int(base_width * scale), int(base_height * scale))
    )
    base_rect = scaled_base.get_rect(center=VENTANA.get_rect().center)

    eye_img = IMAGENES_OJOS.get(eye_key, IMAGENES_OJOS["idle"])

    # Si está hablando, boca animada; si no, la que indica mouth_key
    if is_speaking:
        mouth_img = IMAGENES_BOCAS.get(current_mouth_key, IMAGENES_BOCAS["Idle"])
    else:
        mouth_img = IMAGENES_BOCAS.get(mouth_key, IMAGENES_BOCAS["Idle"])

    scaled_eye = pygame.transform.smoothscale(
        eye_img,
        (int(eye_img.get_width() * scale), int(eye_img.get_height() * scale))
    )
    scaled_mouth = pygame.transform.smoothscale(
        mouth_img,
        (int(mouth_img.get_width() * scale), int(mouth_img.get_height() * scale))
    )

    pos_eye = get_absolute_position(scaled_eye, base_rect, CENTRO_OJOS_RELATIVO)
    pos_mouth = get_absolute_position(scaled_mouth, base_rect, CENTRO_BOCA_RELATIVO)

    VENTANA.blit(scaled_base, base_rect)
    VENTANA.blit(scaled_eye, pos_eye)
    VENTANA.blit(scaled_mouth, pos_mouth)

    if displayed_text:
        font_size = int(20 * scale)
        font = pygame.font.SysFont("Arial", font_size)
        text_surface = font.render(displayed_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(ANCHO_PANTALLA // 2, ALTO_PANTALLA - int(40 * scale)))
        VENTANA.blit(text_surface, text_rect)

    pygame.display.flip()

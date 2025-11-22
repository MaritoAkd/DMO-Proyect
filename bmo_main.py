import pygame
import threading
import time
import os
import bmo_gui as gui
from chat import responder, EYES_NAMES, MOUTH_NAMES
from audio_manager import audio_manager
from text_editor import TextEditor

pygame.init()

# ===== MAPEO DE IDS A NOMBRES DE ARCHIVOS =====
EYES_ID_TO_KEY = {
    0: "angry", 1: "bad", 2: "closed", 3: "cry", 4: "crying",
    5: "emocion", 6: "idle", 7: "judge", 8: "shock", 
    9: "thinking", 10: "tired"
}

MOUTH_ID_TO_KEY = {
    0: "Idle", 1: "Question"
}

# ===== ESTADO DE DMO =====
class DMOState:
    """Clase para manejar el estado de DMO de forma limpia"""
    
    def __init__(self):
        # Estado visual
        self.current_state = "idle"  # idle, listening, thinking, speaking
        self.eye_key = "idle"
        self.mouth_key = "Idle"
        self.talking_frame = 1
        self.last_talking_switch = time.time()
        self.displayed_text = ""
        
        # Estado de audio
        self.is_listening = False
        self.is_processing = False
        
        # Estado de UI
        self.app_state = "BMO_FACE"  # BMO_FACE, MENU_APARIENCIA, MENU_PROFESIONAL, TEXT_EDITOR
        
        # Lock para thread safety
        self._lock = threading.Lock()
    
    def set_expression(self, eye_id, mouth_id, text=""):
        """Actualiza la expresión de DMO thread-safe"""
        with self._lock:
            self.eye_key = EYES_ID_TO_KEY.get(eye_id, "idle")
            self.mouth_key = MOUTH_ID_TO_KEY.get(mouth_id, "Idle")
            self.displayed_text = text
    
    def set_state(self, state):
        """Cambia el estado general de DMO"""
        with self._lock:
            self.current_state = state
    
    def get_visual_state(self):
        """Retorna el estado visual actual para el GUI"""
        with self._lock:
            return {
                "state": self.current_state,
                "eye_key": self.eye_key,
                "mouth_key": self.mouth_key,
                "talking_frame": self.talking_frame,
                "displayed_text": self.displayed_text
            }

# ===== INICIALIZACIÓN =====
dmo = DMOState()

# Menús
menu = gui.HamburgerMenu()
appearance_menu = gui.AppearanceMenu()
professional_menu = gui.ProfessionalMenu()

# Editores
directorio_base = os.path.dirname(__file__)
editor_historial = TextEditor("Cerebro DMO (Historial)", os.path.join(directorio_base, "historial_tmo.txt"))
editor_notas = TextEditor("Notas del Profesional", os.path.join(directorio_base, "Professional_notes.txt"))
editor_personalidad = TextEditor("Personalidad del Usuario", os.path.join(directorio_base, "User_personality.txt"))
current_editor = None

# ===== Sincronización TTS <-> GUI =====
def _on_tts_start():
    try:
        # Indicar visualmente que DMO está hablando
        gui.is_speaking = True
        dmo.set_state("speaking")
        dmo.last_talking_switch = time.time()
    except Exception:
        pass

def _on_tts_end():
    try:
        gui.is_speaking = False
        # Dejar un pequeño margen y volver a idle
        dmo.set_state("idle")
        dmo.set_expression(6, 0, "")
    except Exception:
        pass

# Registrar callbacks con el AudioManager (usa internals seguros)
try:
    audio_manager.register_on_speech_start(_on_tts_start)
    audio_manager.register_on_speech_end(_on_tts_end)
except Exception:
    pass

# ===== FUNCIONES DE INTERACCIÓN =====
def process_user_input(user_text, speaker=None):
    """
    Procesa el input del usuario y genera respuesta.
    CORREGIDO: Garantiza que los flags se limpien SIEMPRE.
    """
    global dmo
    
    if not user_text or user_text.strip() == "":
        print("[DMO] ⚠️ Input vacío")
        dmo.set_state("idle")
        dmo.set_expression(1, 0, "No escuché nada")  # bad, Idle
        time.sleep(1.5)
        dmo.set_expression(6, 0, "")  # idle, Idle
        dmo.is_processing = False
        return
    
    try:
        # Estado: pensando
        dmo.set_state("thinking")
        dmo.set_expression(9, 1, "Pensando...")  # thinking, Question

        # Obtener respuesta de la IA (con speaker si está disponible)
        print(f"[DMO] 🤔 Procesando: '{user_text}'")
        if speaker:
            print(f"[DMO] 👤 Speaker: {speaker}")
        respuesta = responder(user_text, speaker=speaker, debug=True)

        # Actualizar expresión con la respuesta
        dmo.set_expression(
            respuesta["eyes"], 
            respuesta["mouth"], 
            respuesta["text"]
        )

        # Estado: hablando (el callback de TTS controlará la animación)
        dmo.set_state("speaking")
        print("[DMO] 🎤 Iniciando habla...")

        # Hablar (bloqueante para sincronizar animación)
        audio_manager.speak(respuesta["text"], blocking=True, debug=True)
        print("[DMO] ✅ Habla completada")

    except Exception as e:
        print(f"[DMO] ❌ Error procesando: {e}")
        import traceback
        traceback.print_exc()
        dmo.set_expression(1, 0, "Ups, error...")  # bad, Idle
        time.sleep(1.5)

    finally:
        # CRÍTICO: Limpiar TODOS los flags sin importar qué pasó
        print("[DMO] 🧹 Limpiando estado...")
        # El callback de TTS se encarga de sincronizar gui.is_speaking
        dmo.set_state("idle")
        dmo.set_expression(6, 0, "")  # idle, Idle
        dmo.is_processing = False
        print("[DMO] ✅ Estado limpiado, listo para nueva interacción")

# ===== MANEJO DE MENÚS =====
def handle_menu_option(option):
    """Maneja selección del menú hamburguesa"""
    global dmo
    print(f"[MENU] Opción: {option}")
    
    if option == "Apariencia":
        dmo.app_state = "MENU_APARIENCIA"
    elif option == "Para profesionales":
        dmo.app_state = "MENU_PROFESIONAL"

def handle_professional_option(option):
    """Maneja opciones del menú profesional"""
    global current_editor, dmo
    
    if option == "Cerebro DMO (Historial)":
        current_editor = editor_historial
        current_editor.open()
        dmo.app_state = "TEXT_EDITOR"
    elif option == "Notas del Profesional":
        current_editor = editor_notas
        current_editor.open()
        dmo.app_state = "TEXT_EDITOR"
    elif option == "Personalidad del Usuario":
        current_editor = editor_personalidad
        current_editor.open()
        dmo.app_state = "TEXT_EDITOR"


def main():
    global dmo, current_editor
    
    print("=" * 60)
    print("DMO - Robot Asistente Terapéutico")
    print("=" * 60)
    print("\n[CONTROLES]")
    print("  ESPACIO: Mantener presionado para hablar (push-to-talk)")
    print("  M: Abrir menú")
    print("  R: Recalibrar micrófono")
    print("  ESC: Salir/Volver")
    
    # Info sobre Speaker ID
    if audio_manager.speaker_system:
        speakers = audio_manager.get_registered_speakers()
        if speakers:
            print(f"\n[SPEAKER ID]")
            print(f"  ✅ Activado con {len(speakers)} voces:")
            for s in speakers:
                print(f"     - {s}")
        else:
            print("\n[SPEAKER ID]")
            print("  ⚠️ Disponible pero sin voces registradas")
            print("  Ejecuta: python speaker_recognition.py")
    else:
        print("\n[SPEAKER ID]")
        print("  ❌ No disponible (ejecuta: pip install resemblyzer)")
    
    print("\n[INICIANDO]...\n")
    
    gui.cargar_imagenes()
    clock = pygame.time.Clock()
    running = True
    save_notification_time = 0
    
    # Calibrar micrófono al inicio
    audio_manager.recalibrate()
    
    while running:
        dt = clock.tick(30) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        
        # Actualizar menús
        menu.update(dt)
        if menu.is_open:
            menu.check_hover(mouse_pos)
        
        if dmo.app_state == "MENU_PROFESIONAL":
            professional_menu.check_hover(mouse_pos)
        
        # Actualizar editor
        if dmo.app_state == "TEXT_EDITOR" and current_editor:
            current_editor.update(dt)
        
        # Eventos
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            
            # Editor activo
            elif dmo.app_state == "TEXT_EDITOR" and current_editor:
                result = current_editor.handle_event(e, gui.VENTANA.get_rect(), gui.imagen_base_bmo)
                if result == "CLOSE":
                    current_editor.close()
                    dmo.app_state = "MENU_PROFESIONAL"
                    current_editor = None
                elif result == "SAVED":
                    save_notification_time = time.time()
                    print(f"[EDITOR] 💾 Guardado: {current_editor.file_path}")
            
            # Teclado
            elif e.type == pygame.KEYDOWN:
                # ESC
                if e.key == pygame.K_ESCAPE:
                    if dmo.app_state in ["MENU_APARIENCIA", "MENU_PROFESIONAL"]:
                        dmo.app_state = "BMO_FACE"
                    else:
                        running = False
                
                # M - Menu
                elif e.key == pygame.K_m:
                    menu.toggle()
                
                # ESPACIO - PRESIONAR: Empezar a grabar
                elif e.key == pygame.K_SPACE and dmo.app_state == "BMO_FACE":
                    if not menu.is_open and not dmo.is_processing and not dmo.is_listening:
                        print("[DMO] 👂 Presiona ESPACIO - Grabando...")
                        dmo.is_listening = True
                        dmo.set_state("listening")
                        dmo.set_expression(9, 1, "Escuchando...")  # thinking, Question
                        audio_manager.start_listening(debug=True)
                
                # R - Recalibrar micrófono
                elif e.key == pygame.K_r:
                    print("[DMO] 🔄 Recalibrando micrófono...")
                    audio_manager.recalibrate()
            
            # ESPACIO - SOLTAR: Procesar audio
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE and dmo.is_listening:
                    print("[DMO] 🔴 Suelta ESPACIO - Procesando...")
                    dmo.is_listening = False
                    dmo.set_expression(9, 0, "Procesando...")  # thinking, Idle
                    
                    # Primero detener la grabación en el thread principal
                    print("[DMO] ℹ️ Deteniendo grabación...")
                    audio = audio_manager.speech.stop_recording(debug=True)
                    
                    # Luego procesar el audio en thread separado
                    def process_audio():
                        if audio:  # Si se capturó audio
                            # Reconocer texto + speaker
                            result = audio_manager.recognize_with_speaker(audio, debug=True)
                            
                            text = result['text']
                            speaker = result['speaker']
                            confidence = result['confidence']
                            
                            if text and text.strip():
                                dmo.is_processing = True
                                
                                # Mostrar info del speaker
                                if speaker:
                                    print(f"[DMO] 👤 Detectado: {speaker} (confianza: {confidence:.0%})")
                                else:
                                    if confidence > 0:
                                        print(f"[DMO] 👤 Speaker desconocido (mejor match: {confidence:.0%})")
                                    else:
                                        print(f"[DMO] 👤 No se pudo identificar speaker")
                                
                                process_user_input(text, speaker=speaker)
                            else:
                                print("[DMO] ❓ No pude entender el audio")
                                dmo.set_state("idle")
                                dmo.set_expression(1, 0, "No entendí lo que dijiste")  # bad, Idle
                                time.sleep(1.5)
                                dmo.set_expression(6, 0, "")  # idle, Idle
                        else:
                            print("[DMO] ❓ No se capturó audio")
                            dmo.set_state("idle")
                            dmo.set_expression(1, 0, "No te escuché")  # bad, Idle
                            time.sleep(1.5)
                            dmo.set_expression(6, 0, "")  # idle, Idle
                    
                    threading.Thread(target=process_audio, daemon=True).start()
            
            # Mouse
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # Menú hamburguesa
                action = menu.check_click(mouse_pos)
                if action and action != "TOGGLE":
                    handle_menu_option(action)
                
                # Menú apariencia
                if dmo.app_state == "MENU_APARIENCIA":
                    result = appearance_menu.handle_event(e)
                    if result == "BACK":
                        dmo.app_state = "BMO_FACE"
                    elif result:
                        gui.set_active_skin(result)
                
                # Menú profesional
                elif dmo.app_state == "MENU_PROFESIONAL":
                    result = professional_menu.handle_event(e)
                    if result == "BACK":
                        dmo.app_state = "BMO_FACE"
                    elif result in professional_menu.options:
                        handle_professional_option(result)
        
        # Animación de boca al hablar
        visual_state = dmo.get_visual_state()
        
        if visual_state["state"] == "speaking" and audio_manager.is_speaking:
            if time.time() - dmo.last_talking_switch > 0.15:
                dmo.talking_frame = (dmo.talking_frame % 4) + 1
                dmo.last_talking_switch = time.time()
        else:
            dmo.talking_frame = 1
        
        # Renderizado
        if dmo.app_state == "TEXT_EDITOR" and current_editor:
            # Fondo + editor
            try:
                if gui.imagen_base_bmo is not None:
                    base_width, base_height = gui.imagen_base_bmo.get_size()
                    scale = min(gui.ANCHO_PANTALLA / base_width, gui.ALTO_PANTALLA / base_height)
                    new_width = int(base_width * scale)
                    new_height = int(base_height * scale)
                    scaled_base = pygame.transform.smoothscale(gui.imagen_base_bmo, (new_width, new_height))
                    base_rect = scaled_base.get_rect(center=gui.VENTANA.get_rect().center)
                    gui.VENTANA.blit(scaled_base, base_rect)
                else:
                    gui.VENTANA.fill((0, 0, 0))
            except:
                gui.VENTANA.fill((0, 0, 0))
            
            current_editor.draw(gui.VENTANA, gui.VENTANA.get_rect(), gui.imagen_base_bmo)
            
            # Notificación guardado
            if save_notification_time > 0 and time.time() - save_notification_time < 2:
                notif_font = pygame.font.SysFont("Arial", 20)
                notif_surf = notif_font.render("¡Guardado!", True, (100, 255, 100))
                notif_rect = notif_surf.get_rect(center=(gui.ANCHO_PANTALLA // 2, 50))
                gui.VENTANA.blit(notif_surf, notif_rect)
        
        else:
            # Cara de DMO
            gui.draw_bmo(
                state=visual_state["state"],
                eye_key=visual_state["eye_key"],
                mouth_key=visual_state["mouth_key"],
                talking_frame=dmo.talking_frame,
                displayed_text=visual_state["displayed_text"],
                menu=menu,
                app_state=dmo.app_state,
                appearance_menu=appearance_menu,
                professional_menu=professional_menu
            )
        
        pygame.display.flip()
    
    pygame.quit()
    print("\n[DMO] 👋 ¡Hasta luego!")

if __name__ == "__main__":
    main()
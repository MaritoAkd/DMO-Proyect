import pygame
import threading
import time
import pyttsx3
import speech_recognition as sr

import bmo_gui as gui
from chat import responder

pygame.init()

# Estado compartido
current_state = "idle"      # idle, thinking, speaking
current_eye_key = "idle"
current_mouth_key = "Idle"
talking_frame = 1
last_talking_switch = time.time()
displayed_text = ""

listening = False
audio_data = None
recognizer = sr.Recognizer()
mic = sr.Microphone()

# Lock para el TTS
tts_lock = threading.Lock()

def configurar_engine():
    """Configura un nuevo engine TTS con los parámetros correctos"""
    engine = pyttsx3.init()
    engine.setProperty('rate', 120)
    
    # Configurar voz en español
    voices = engine.getProperty('voices')
    for v in voices:
        if 'es' in v.id.lower() or 'spanish' in v.name.lower():
            engine.setProperty('voice', v.id)
            break
    
    return engine

def hablar_texto(texto):
    """Función segura para hablar texto con TTS"""
    with tts_lock:
        try:
            # Crear nuevo engine para cada uso
            engine = configurar_engine()
            engine.say(texto)
            engine.runAndWait()
            # Cleanup explícito
            engine.stop()
            del engine
        except Exception as e:
            print(f"Error en TTS: {e}")

def escuchar_en_hilo():
    """Escucha mientras la barra se mantiene presionada y acumula fragmentos"""
    global audio_data, listening
    audio_chunks = []

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Escuchando...")
            while listening:  # mientras el usuario mantenga la barra
                try:
                    # Timeout corto para no bloquear el hilo
                    chunk = recognizer.listen(source, timeout=0.5, phrase_time_limit=2)
                    audio_chunks.append(chunk)
                except sr.WaitTimeoutError:
                    pass  # no pasa nada, seguimos escuchando
    except Exception as e:
        print(f"Error escuchando: {e}")

    # Una vez que se suelta la barra, combinamos todos los fragmentos
    if audio_chunks:
        # Concatenar audios: creamos un solo AudioData combinando los raw_data
        raw = b''.join(chunk.get_raw_data() for chunk in audio_chunks)
        sample_rate = audio_chunks[0].sample_rate
        sample_width = audio_chunks[0].sample_width
        audio_data = sr.AudioData(raw, sample_rate, sample_width)
    else:
        audio_data = None

    listening = False


def process_and_speak(user_text):
    global current_state, current_eye_key, current_mouth_key, displayed_text

    try:
        # Estado: pensando
        current_state = "thinking"
        current_eye_key = "thinking"  # Cambié de "thinking" a "emocion" (que existe en tu sistema)
        current_mouth_key = "Question"
        displayed_text = "Pensando..."
        
        # Pequeña pausa para que se vea el cambio de estado
        time.sleep(0.5)

        # Obtener respuesta de la IA
        ai_data = responder(user_text)

        response_text = ai_data.get("text", "Lo siento, no entendí.")
        response_eyes = ai_data.get("eyes", "idle")
        response_mouth = ai_data.get("mouth", "Idle")

        print(f"TMO: {response_text}")

        # Estado: hablando
        current_state = "speaking"
        current_eye_key = response_eyes
        displayed_text = response_text

        # Avisar al gui que estamos hablando (para animación boca)
        gui.is_speaking = True

        # Hablar usando la función segura
        hablar_texto(response_text)

        # Terminado de hablar
        gui.is_speaking = False
        current_state = "idle"
        current_eye_key = response_eyes
        current_mouth_key = response_mouth
        displayed_text = ""
        
        # Pequeña pausa antes de volver a idle completo
        time.sleep(0.5)
        current_eye_key = "idle"
        
    except Exception as e:
        print(f"Error en process_and_speak: {e}")
        # Estado de error
        gui.is_speaking = False
        current_state = "idle"
        current_eye_key = "bad"
        current_mouth_key = "Idle"
        displayed_text = ""

def main():
    global current_state, current_eye_key, current_mouth_key, talking_frame, last_talking_switch, displayed_text
    global listening, audio_data

    clock = pygame.time.Clock()
    print("Mantén presionada la barra para hablar, suelta para enviar. ESC para salir.")

    hilo_escucha = None

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE and not listening and current_state == "idle":
                    print("Iniciando escucha...")
                    listening = True
                    current_eye_key = "emocion"
                    displayed_text = "Escuchando..."
                    audio_data = None

                    # arrancar hilo de escucha basado en fragmentos
                    hilo_escucha = threading.Thread(target=escuchar_en_hilo, daemon=True)
                    hilo_escucha.start()

                elif e.key == pygame.K_ESCAPE:
                    running = False

            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE and listening:
                    print("Soltaste barra, procesando lo dicho...")
                    listening = False
                    current_eye_key = "idle"
                    displayed_text = "Procesando..."

                    # Esperar a que termine el hilo de escucha
                    if hilo_escucha is not None and hilo_escucha.is_alive():
                        hilo_escucha.join(timeout=5)  # espera hasta 5s

                    if audio_data is not None:
                        try:
                            texto_usuario = recognizer.recognize_google(audio_data, language="es-ES")
                            print(f"Tú dijiste: {texto_usuario}")
                            threading.Thread(target=process_and_speak, args=(texto_usuario,), daemon=True).start()
                        except sr.UnknownValueError:
                            print("No entendí lo que dijiste.")
                            current_eye_key = "bad"
                            displayed_text = "No entendí"
                            time.sleep(1)
                            current_eye_key = "idle"
                            displayed_text = ""
                        except sr.RequestError as e:
                            print(f"Error del servicio de reconocimiento: {e}")
                            current_eye_key = "bad"
                            displayed_text = "Error de conexión"
                            time.sleep(1)
                            current_eye_key = "idle"
                            displayed_text = ""
                    else:
                        print("No se capturó audio")
                        current_eye_key = "bad"
                        displayed_text = "No escuché nada"
                        time.sleep(1)
                        current_eye_key = "idle"
                        displayed_text = ""

        # Animación de boca hablando
        if current_state == "speaking":
            if time.time() - last_talking_switch > 0.2:
                talking_frame = (talking_frame % 4) + 1
                last_talking_switch = time.time()
        else:
            talking_frame = 1

        # Dibujar BMO
        gui.draw_bmo(current_state, current_eye_key, current_mouth_key, talking_frame, displayed_text)
        clock.tick(30)

    pygame.quit()
    print("Fin.")





if __name__ == "__main__":
    main()
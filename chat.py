import google.generativeai as genai
import os
import json
from datetime import datetime

# Configuración de Gemini
genai.configure(api_key="AIzaSyCkAy_bWVR-iuJe4GjRGNoG3HwNrYntnjg")  # Cambia tu API KEY aquí
modelo = genai.GenerativeModel("gemini-2.0-flash")

# Carga del historial
historial_file_path = os.path.join(os.path.dirname(__file__), "historial_tmo.txt")
try:
    with open(historial_file_path, "r", encoding="utf-8") as f:
        prompt_base = f.read()
except Exception:
    prompt_base = "Eres un asistente amigable."

# Arranque de sesión
chat = modelo.start_chat(history=[
    {"role": "user", "parts": [prompt_base]}
])

# Seguimiento de tiempo
ultima_interaccion = datetime.now()

def generar_contexto_temporal():
    global ultima_interaccion
    ahora = datetime.now()
    minutos = int((ahora - ultima_interaccion).total_seconds() // 60)
    texto = f"La hora actual es {ahora.strftime('%H:%M')} y han pasado {minutos} minutos desde la última interacción."
    ultima_interaccion = ahora
    return texto

def guardar_mensaje(rol, mensaje):
    # Puedes agregar aquí tu lógica de registro si quieres
    pass

def responder(mensaje_usuario):
    guardar_mensaje("USUARIO", mensaje_usuario)
    contexto = generar_contexto_temporal()

    prompt = (
        f"{contexto}\n{mensaje_usuario}\n\n"
        "Genera una respuesta en formato JSON estricto con estas claves:\n"
        "- \"text\": tu mensaje de respuesta.\n"
        "- \"eyes\": el estado de los ojos (idle, emocion, shock, etc).\n"
        "- \"mouth\": el estado de la boca (Idle, Question, etc).\n"
        "Ejemplo de formato:\n"
        "{\"text\": \"¡Hola! ¿Cómo estás?\", \"eyes\": \"emocion\", \"mouth\": \"Idle\"}"
    )

    try:
        respuesta_ia = chat.send_message(prompt)
        respuesta_str = respuesta_ia.text.strip()

        # Limpieza si viene en bloque Markdown
        if respuesta_str.startswith("```json"):
            respuesta_str = respuesta_str.lstrip("```json").rstrip("```").strip()

        # Intentar parsear JSON
        data = json.loads(respuesta_str)

        # Validar
        if not all(k in data for k in ["text", "eyes", "mouth"]):
            raise ValueError("Respuesta JSON incompleta.")

        guardar_mensaje("TMO", data["text"])
        return data

    except json.JSONDecodeError:
        print(f"ERROR: JSON inválido:\n{respuesta_str}")
        return {
            "text": "Disculpa, no entendí bien tu pregunta. ¿Puedes repetirla?",
            "eyes": "bad",
            "mouth": "Idle"
        }
    except Exception as e:
        print(f"ERROR en la IA: {e}")
        return {
            "text": "Lo siento, hubo un problema técnico al responder.",
            "eyes": "shock",
            "mouth": "Idle"
        }

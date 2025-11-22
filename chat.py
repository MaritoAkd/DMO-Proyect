import google.generativeai as genai
import os
import json
from datetime import datetime
import threading
import re

# ===== CONFIGURACIÓN =====
genai.configure(api_key="AIzaSyD7ooN1g9aZ9cMsbOu_l6-sUIYnlw8TQ-I")
modelo = genai.GenerativeModel("gemini-2.5-flash")

# Rutas de archivos
historial_file_path = os.path.join(os.path.dirname(__file__), "historial_tmo.txt")
personality_file_path = os.path.join(os.path.dirname(__file__), "User_personality.txt")

# ===== MAPEO DE EXPRESIONES =====
EYES_MAP = {
    "angry": 0, "bad": 1, "closed": 2, "cry": 3, "crying": 4,
    "emocion": 5, "idle": 6, "judge": 7, "shock": 8, 
    "thinking": 9, "tired": 10
}

MOUTH_MAP = {
    "Idle": 0, "Question": 1
}

# Mapeo inverso para debugging
EYES_NAMES = {v: k for k, v in EYES_MAP.items()}
MOUTH_NAMES = {v: k for k, v in MOUTH_MAP.items()}

# ===== CACHE DE CONTEXTO =====
_context_cache = None
_context_timestamp = 0
_cache_lock = threading.Lock()
CACHE_DURATION = 300  # 5 minutos

def cargar_contexto():
    """Carga y cachea el contexto para evitar lecturas constantes"""
    global _context_cache, _context_timestamp
    
    with _cache_lock:
        # Usar cache si es reciente
        if _context_cache and (datetime.now().timestamp() - _context_timestamp) < CACHE_DURATION:
            return _context_cache
        
        # Cargar historial base
        try:
            with open(historial_file_path, "r", encoding="utf-8") as f:
                historial_context = f.read()
        except Exception:
            historial_context = "Eres DMO, un asistente adorable y curioso."
        
        # Cargar personalidad del usuario
        personalidad_usuario = ""
        nombre_usuario = None
        try:
            with open(personality_file_path, "r", encoding="utf-8") as f:
                personalidad_usuario = f.read()
                if "Su nombre es:" in personalidad_usuario:
                    nombre_usuario = personalidad_usuario.split("Su nombre es:")[1].split("\n")[0].strip()
        except Exception:
            pass
        
        # Construir prompt optimizado
        prompt_base = historial_context
        
        # Modificar según si conocemos el nombre
        if nombre_usuario:
            prompt_base = prompt_base.replace(
                "- No sabes quién te habla al principio de una sesión. Podés preguntar el nombre con curiosidad e ilusión.",
                f"- Ya conocés al usuario, se llama {nombre_usuario}. Tratalo con cariño y familiaridad."
            )
        
        # Agregar contexto de personalidad si existe
        if personalidad_usuario:
            prompt_base = (
                f"=== CONTEXTO DEL USUARIO (uso interno, no mencionar) ===\n"
                f"{personalidad_usuario}\n"
                f"=== FIN CONTEXTO ===\n\n"
                f"{prompt_base}"
            )
        
        # Actualizar instrucciones de respuesta con IDs numéricos
        prompt_base += f"\n\n=== FORMATO DE RESPUESTA OBLIGATORIO ===\n"
        prompt_base += "SIEMPRE responde con un JSON con estas claves:\n"
        prompt_base += '- "text": tu mensaje (máximo 120 caracteres)\n'
        prompt_base += f'- "eyes": ID numérico de 0-10 (0=angry, 1=bad, 2=closed, 3=cry, 4=crying, 5=emocion, 6=idle, 7=judge, 8=shock, 9=thinking, 10=tired)\n'
        prompt_base += f'- "mouth": ID numérico 0-1 (0=Idle, 1=Question)\n\n'
        prompt_base += 'Ejemplo: {"text": "¡Hola amigo!", "eyes": 5, "mouth": 0}\n'
        prompt_base += "NO uses markdown (```json), SOLO JSON puro sin saltos de línea extra.\n"
        prompt_base += "IMPORTANTE: Tu respuesta debe empezar directamente con { y terminar con }\n"
        
        _context_cache = prompt_base
        _context_timestamp = datetime.now().timestamp()
        
        return _context_cache

# ===== INICIALIZACIÓN DEL CHAT =====
chat = None
chat_lock = threading.Lock()

def get_chat():
    """Obtiene o crea instancia de chat thread-safe"""
    global chat
    with chat_lock:
        if chat is None:
            prompt_base = cargar_contexto()
            chat = modelo.start_chat(history=[
                {"role": "user", "parts": [prompt_base]}
            ])
        return chat

def limpiar_json_response(raw_text):
    """
    Limpia la respuesta de la IA para extraer solo el JSON válido.
    
    Maneja casos como:
    - Markdown: ```json\n{...}\n```
    - JSON duplicado: {"text": "\n{"text": ...
    - Texto adicional: Aquí está: {...}
    """
    # Eliminar markdown
    if "```" in raw_text:
        # Extraer contenido entre ```
        parts = raw_text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                raw_text = part
                break
    
    # Buscar el JSON válido (primer { al último } balanceado)
    start_idx = raw_text.find("{")
    if start_idx == -1:
        raise ValueError("No se encontró inicio de JSON")
    
    # Encontrar el } correspondiente
    count = 0
    end_idx = -1
    for i in range(start_idx, len(raw_text)):
        if raw_text[i] == "{":
            count += 1
        elif raw_text[i] == "}":
            count -= 1
            if count == 0:
                end_idx = i
                break
    
    if end_idx == -1:
        raise ValueError("JSON sin cerrar")
    
    json_str = raw_text[start_idx:end_idx+1]
    
    # Limpiar saltos de línea dentro de strings (causa del error "Invalid control character")
    # Usar regex para encontrar strings y reemplazar \n por espacio
    def replace_newlines_in_strings(match):
        return match.group(0).replace('\n', ' ').replace('\r', ' ')
    
    # Patrón: "texto que puede tener \n"
    json_str = re.sub(r'"[^"]*"', replace_newlines_in_strings, json_str)
    
    return json_str

# ===== FUNCIÓN PRINCIPAL DE RESPUESTA =====
def responder(texto_usuario, speaker=None, debug=False):
    """
    Genera respuesta de DMO de forma optimizada, considerando quién habla
    
    Args:
        texto_usuario: Texto del usuario
        speaker: Nombre del speaker identificado (opcional)
        debug: Si True, imprime información de debug
        
    Returns:
        dict con keys: text, eyes, mouth (valores numéricos)
    """
    if debug:
        if speaker:
            print(f"\n[DMO] 👤 {speaker} dice: '{texto_usuario}'")
        else:
            print(f"\n[DMO] Usuario: '{texto_usuario}'")
    
    try:
        chat_instance = get_chat()
        
        # Construir prompt considerando el speaker
        if speaker:
            prompt = f"[SPEAKER: {speaker}] USUARIO: {texto_usuario}\n\nRespuesta JSON:"
        else:
            prompt = f"[SPEAKER: Desconocido] USUARIO: {texto_usuario}\n\nRespuesta JSON:"
        
        # Enviar mensaje
        start_time = datetime.now()
        respuesta_ia = chat_instance.send_message(prompt)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if debug:
            print(f"[DMO] IA respondió en {elapsed:.2f}s")
        
        # Procesar respuesta
        respuesta_str = respuesta_ia.text.strip()
        
        # Limpiar JSON
        try:
            json_limpio = limpiar_json_response(respuesta_str)
            data = json.loads(json_limpio)
        except Exception as e:
            if debug:
                print(f"[DMO] Error parseando, raw: {respuesta_str[:200]}")
            raise
        
        # Validar estructura
        if not all(k in data for k in ["text", "eyes", "mouth"]):
            raise ValueError("JSON incompleto")
        
        # Validar tipos y rangos
        if not isinstance(data["eyes"], int) or not (0 <= data["eyes"] <= 10):
            raise ValueError(f"eyes inválido: {data['eyes']}")
        
        if not isinstance(data["mouth"], int) or not (0 <= data["mouth"] <= 1):
            raise ValueError(f"mouth inválido: {data['mouth']}")
        
        if debug:
            print(f"[DMO] Respuesta: '{data['text']}'")
        
        return data
        
    except json.JSONDecodeError as e:
        if debug:
            print(f"[DMO] Error JSON: {e}")
        
        return {
            "text": "Perdón, me trabé un poco. ¿Repetís?",
            "eyes": 1,  # bad
            "mouth": 0  # Idle
        }
        
    except Exception as e:
        if debug:
            print(f"[DMO] Error: {e}")
        
        return {
            "text": "Uy, algo salió mal. ¿Probamos de nuevo?",
            "eyes": 1,  # bad
            "mouth": 0  # Idle
        }

# ===== FUNCIÓN DE LIMPIEZA =====
def limpiar_cache():
    """Limpia el cache de contexto (útil si se modifican archivos)"""
    global _context_cache, chat
    with _cache_lock:
        _context_cache = None
    with chat_lock:
        chat = None
    print("[DMO] Cache limpiado")
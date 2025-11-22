# pip install pyannote.audio
# pip install resemblyzer  # Alternativa más simple

import numpy as np
import pickle
import os
from resemblyzer import VoiceEncoder, preprocess_wav
import sounddevice as sd
import tempfile
import wave

class SpeakerRecognitionSystem:
    """Sistema para reconocer diferentes voces"""
    
    def __init__(self, profiles_path="voice_profiles.pkl"):
        print("[SpeakerID] Cargando modelo de voces...")
        self.encoder = VoiceEncoder()
        self.profiles_path = profiles_path
        self.voice_profiles = {}  # {nombre: embedding_promedio}
        self.load_profiles()
        print("[SpeakerID] ¡Listo!")
        
    def load_profiles(self):
        """Carga perfiles de voz guardados"""
        if os.path.exists(self.profiles_path):
            try:
                with open(self.profiles_path, 'rb') as f:
                    self.voice_profiles = pickle.load(f)
                print(f"[SpeakerID] Cargados {len(self.voice_profiles)} perfiles")
            except Exception as e:
                print(f"[SpeakerID] Error cargando perfiles: {e}")
                self.voice_profiles = {}
        else:
            print("[SpeakerID] No hay perfiles guardados")
            
    def save_profiles(self):
        """Guarda perfiles de voz"""
        try:
            with open(self.profiles_path, 'wb') as f:
                pickle.dump(self.voice_profiles, f)
            print(f"[SpeakerID] Guardados {len(self.voice_profiles)} perfiles")
        except Exception as e:
            print(f"[SpeakerID] Error guardando: {e}")
            
    def register_voice(self, name, audio_samples, sample_rate=16000):
        """
        Registra una nueva voz en el sistema
        
        Args:
            name: Nombre de la persona
            audio_samples: Lista de numpy arrays con muestras de audio
            sample_rate: Frecuencia de muestreo
        """
        if not audio_samples:
            print("[SpeakerID] No hay muestras de audio")
            return False
            
        print(f"[SpeakerID] Registrando voz de '{name}' con {len(audio_samples)} muestras...")
        
        embeddings = []
        for i, audio in enumerate(audio_samples):
            try:
                # Convertir a float32 si es necesario
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32) / 32768.0
                    
                # Generar embedding
                embedding = self.encoder.embed_utterance(audio)
                embeddings.append(embedding)
                print(f"  Muestra {i+1}/{len(audio_samples)} procesada")
            except Exception as e:
                print(f"  Error en muestra {i+1}: {e}")
                
        if not embeddings:
            print("[SpeakerID] No se pudo procesar ninguna muestra")
            return False
            
        # Promedio de embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        self.voice_profiles[name] = avg_embedding
        self.save_profiles()
        
        print(f"[SpeakerID] ✅ Voz de '{name}' registrada")
        return True
        
    def identify_speaker(self, audio, sample_rate=16000, threshold=0.75):
        """
        Identifica quién está hablando
        
        Args:
            audio: numpy array con el audio
            sample_rate: Frecuencia de muestreo
            threshold: Umbral de similitud (0-1, más alto = más estricto)
            
        Returns:
            tuple: (nombre, confianza) o (None, 0) si no se identifica
        """
        if not self.voice_profiles:
            print("[SpeakerID] No hay perfiles registrados")
            return None, 0.0
            
        try:
            # Convertir a float32 si es necesario
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32) / 32768.0
                
            # Generar embedding del audio
            embedding = self.encoder.embed_utterance(audio)
            
            # Comparar con todos los perfiles
            best_match = None
            best_similarity = 0.0
            
            for name, profile_embedding in self.voice_profiles.items():
                # Similitud coseno
                similarity = np.dot(embedding, profile_embedding) / (
                    np.linalg.norm(embedding) * np.linalg.norm(profile_embedding)
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = name
                    
            print(f"[SpeakerID] Mejor match: '{best_match}' ({best_similarity:.2%})")
            
            # Verificar umbral
            if best_similarity >= threshold:
                return best_match, best_similarity
            else:
                return None, best_similarity
                
        except Exception as e:
            print(f"[SpeakerID] Error identificando: {e}")
            return None, 0.0
            
    def remove_profile(self, name):
        """Elimina un perfil de voz"""
        if name in self.voice_profiles:
            del self.voice_profiles[name]
            self.save_profiles()
            print(f"[SpeakerID] Perfil '{name}' eliminado")
            return True
        return False
        
    def list_profiles(self):
        """Lista todos los perfiles registrados"""
        return list(self.voice_profiles.keys())


# ===== UTILIDAD PARA REGISTRAR VOCES =====

def record_voice_samples(num_samples=3, duration=3):
    """
    Graba muestras de voz para registro
    
    Args:
        num_samples: Número de muestras a grabar
        duration: Duración de cada muestra en segundos
        
    Returns:
        Lista de numpy arrays con las muestras
    """
    samples = []
    sample_rate = 16000
    
    print(f"\n🎤 Vamos a grabar {num_samples} muestras de {duration} segundos cada una")
    print("Tip: Habla naturalmente, como si conversaras con DMO\n")
    
    for i in range(num_samples):
        input(f"Presiona ENTER para grabar muestra {i+1}/{num_samples}...")
        
        print(f"🔴 GRABANDO {duration}s... ¡Habla ahora!")
        audio = sd.rec(int(duration * sample_rate), 
                       samplerate=sample_rate, 
                       channels=1, 
                       dtype='int16')
        sd.wait()
        print("✅ Muestra grabada\n")
        
        samples.append(audio.flatten())
        
    return samples


# ===== SCRIPT DE REGISTRO INTERACTIVO =====

def interactive_registration():
    """Script para registrar nuevas voces"""
    speaker_system = SpeakerRecognitionSystem()
    
    print("\n" + "="*50)
    print("SISTEMA DE REGISTRO DE VOCES - DMO")
    print("="*50)
    
    while True:
        print("\n¿Qué deseas hacer?")
        print("1. Registrar nueva voz")
        print("2. Ver perfiles registrados")
        print("3. Eliminar perfil")
        print("4. Salir")
        
        choice = input("\nOpción: ").strip()
        
        if choice == "1":
            name = input("\n👤 Nombre de la persona: ").strip()
            if not name:
                print("❌ Nombre inválido")
                continue
                
            if name in speaker_system.voice_profiles:
                confirm = input(f"⚠️  '{name}' ya existe. ¿Sobrescribir? (s/n): ")
                if confirm.lower() != 's':
                    continue
                    
            samples = record_voice_samples(num_samples=3, duration=3)
            speaker_system.register_voice(name, samples)
            
        elif choice == "2":
            profiles = speaker_system.list_profiles()
            if profiles:
                print(f"\n📋 Perfiles registrados ({len(profiles)}):")
                for name in profiles:
                    print(f"  - {name}")
            else:
                print("\n📋 No hay perfiles registrados")
                
        elif choice == "3":
            name = input("\n👤 Nombre a eliminar: ").strip()
            if speaker_system.remove_profile(name):
                print(f"✅ Perfil '{name}' eliminado")
            else:
                print(f"❌ Perfil '{name}' no encontrado")
                
        elif choice == "4":
            print("\n👋 ¡Hasta luego!")
            break


if __name__ == "__main__":
    interactive_registration()
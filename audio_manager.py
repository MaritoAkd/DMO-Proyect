import speech_recognition as sr
from vosk import Model, KaldiRecognizer
import pyttsx3
import threading
import json
import time
import numpy as np

try:
    import sounddevice as sd
    _HAS_SD = True
except Exception:
    sd = None
    _HAS_SD = False

# Importar sistema de reconocimiento de voces
try:
    from speaker_recognition import SpeakerRecognitionSystem
    _HAS_SPEAKER_ID = True
except ImportError:
    _HAS_SPEAKER_ID = False
    print("[AudioManager] ⚠️ speaker_recognition no disponible - ejecuta: pip install resemblyzer")


# ===== TTS MANAGER =====
class TTSManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        # Callbacks que se ejecutan cuando empieza/termina el habla
        self._on_start_callbacks = []
        self._on_end_callbacks = []
        
    def _calculate_duration(self, text):
        """Calcula duración conservadora del habla."""
        if not text:
            return 0.5
        
        words = len(text.split())
        words_per_second = 2.0  # Ajustado más conservador
        
        duration = words / words_per_second
        
        # Pausas por puntuación
        duration += text.count('.') * 0.5
        duration += text.count(',') * 0.3
        duration += text.count('!') * 0.5
        duration += text.count('?') * 0.5
        duration += text.count(';') * 0.4
        
        # Overhead
        duration += 0.8
        
        return max(1.5, duration)

    def speak(self, text, blocking=True, debug=False):
        """Habla usando nuevo engine cada vez."""
        with self._lock:
            engine = None
            try:
                self._is_speaking = True
                # Notificar inicio de habla
                try:
                    for cb in list(self._on_start_callbacks):
                        try:
                            cb()
                        except Exception:
                            pass
                except Exception:
                    pass
                expected_duration = self._calculate_duration(text)
                start_time = time.time()
                
                engine = pyttsx3.init()
                
                # Reducir velocidad
                try:
                    rate = engine.getProperty('rate')
                    if rate:
                        engine.setProperty('rate', int(rate * 0.85))
                except:
                    pass
                
                engine.say(text)
                engine.runAndWait()
                # pyttsx3 finished playback here – notificar fin de habla
                try:
                    for cb in list(self._on_end_callbacks):
                        try:
                            cb()
                        except Exception:
                            pass
                except Exception:
                    pass

                # Marcar que ya no se está hablando (aunque mantenemos un padding opcional)
                self._is_speaking = False

                # Padding conservador después de la reproducción real (no bloquea la notificación)
                elapsed = time.time() - start_time
                remaining = expected_duration - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                    
            except Exception as e:
                print(f"[TTS] Error: {e}")
            finally:
                if engine:
                    try:
                        engine.stop()
                    except:
                        pass
                    del engine
        
    @property
    def is_speaking(self):
        return self._is_speaking

    # Registro de callbacks para inicio/fin de habla
    def register_on_start(self, callback):
        try:
            if callable(callback):
                self._on_start_callbacks.append(callback)
        except Exception:
            pass

    def register_on_end(self, callback):
        try:
            if callable(callback):
                self._on_end_callbacks.append(callback)
        except Exception:
            pass

    def unregister_on_start(self, callback):
        try:
            if callback in self._on_start_callbacks:
                self._on_start_callbacks.remove(callback)
        except Exception:
            pass

    def unregister_on_end(self, callback):
        try:
            if callback in self._on_end_callbacks:
                self._on_end_callbacks.remove(callback)
        except Exception:
            pass


# ===== SPEECH RECOGNIZER =====
class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.model = Model("model")
        self.recognizer_vosk = None  # Se reinicia en cada grabación
        self._is_recording = False
        self._sd_stream = None
        self._sd_frames = []
        self.device_index = 1

    def calibrate(self, duration=1.0):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            print(f"[SR] Calibrado, threshold={self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"[SR] Error calibrando: {e}")

    def start_recording(self, debug=True):
        """Empieza grabación LIMPIA."""
        if self._is_recording:
            return
            
        # CRÍTICO: Reiniciar recognizer de Vosk para limpiar estado
        try:
            self.recognizer_vosk = KaldiRecognizer(self.model, 16000)
            if debug:
                print("[SR] Vosk reiniciado (estado limpio)")
        except Exception as e:
            print(f"[SR] Error reiniciando Vosk: {e}")
            
        self._is_recording = True
        self._sd_frames = []

        try:
            if self.device_index is None:
                default_in = sd.default.device[0]
                self.device_index = default_in

            def _sd_callback(indata, frames, time_info, status):
                if status and debug:
                    print(f"[SR] status: {status}")
                self._sd_frames.append(indata.copy().tobytes())

            self._sd_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='int16',
                callback=_sd_callback,
                device=self.device_index
            )
            self._sd_stream.start()
            if debug:
                print("[SR] Grabando...")
        except Exception as e:
            print(f"[SR] Error iniciando: {e}")
            self._is_recording = False
            self._sd_stream = None

    def stop_recording(self, debug=True):
        """Detiene grabación."""
        if not self._is_recording:
            return None

        self._is_recording = False
        raw = None

        try:
            if self._sd_stream:
                self._sd_stream.stop()
                self._sd_stream.close()
                self._sd_stream = None
                
            if self._sd_frames:
                raw = b"".join(self._sd_frames)
                if debug:
                    print(f"[SR] Audio: {len(raw)} bytes")
            else:
                if debug:
                    print("[SR] Sin frames")
        except Exception as e:
            print(f"[SR] Error deteniendo: {e}")

        if raw:
            return sr.AudioData(raw, 16000, 2)
        return None

    def recognize(self, audio, debug=True):
        """Reconoce texto LIMPIO desde audio."""
        if audio is None:
            return None

        try:
            if isinstance(audio, bytes):
                data = audio
            else:
                data = audio.get_raw_data(convert_rate=16000, convert_width=2)

            if self.recognizer_vosk is not None:
                try:
                    # CRÍTICO: AcceptWaveform con recognizer LIMPIO
                    if self.recognizer_vosk.AcceptWaveform(data):
                        result = json.loads(self.recognizer_vosk.Result())
                        text = result.get('text', '').strip()
                        if debug and text:
                            print(f"[SR] Texto: '{text}'")
                        return text if text else None
                    else:
                        partial = json.loads(self.recognizer_vosk.PartialResult())
                        text = partial.get('partial', '').strip()
                        if text:
                            if debug:
                                print(f"[SR] Parcial: '{text}'")
                            return text
                        return None
                except Exception as e:
                    print(f"[SR] Error Vosk: {e}")
                    return None
            return None
        except Exception as e:
            print(f"[SR] Error recognize: {e}")
            return None


# ===== AUDIO MANAGER =====
class AudioManager:
    def __init__(self):
        self.tts = TTSManager()
        self.sr = SpeechRecognizer()
        self.speech = self.sr
        
        # Sistema de reconocimiento de voces
        if _HAS_SPEAKER_ID:
            try:
                self.speaker_system = SpeakerRecognitionSystem()
                print(f"[AudioManager] ✅ Speaker ID activado ({len(self.speaker_system.voice_profiles)} perfiles)")
            except Exception as e:
                print(f"[AudioManager] ⚠️ Error inicializando Speaker ID: {e}")
                self.speaker_system = None
        else:
            self.speaker_system = None

    # Passthrough para registro de callbacks de habla
    def register_on_speech_start(self, callback):
        try:
            self.tts.register_on_start(callback)
        except Exception as e:
            print(f"[AudioManager] Error register_on_speech_start: {e}")

    def register_on_speech_end(self, callback):
        try:
            self.tts.register_on_end(callback)
        except Exception as e:
            print(f"[AudioManager] Error register_on_speech_end: {e}")

    def unregister_on_speech_start(self, callback):
        try:
            self.tts.unregister_on_start(callback)
        except Exception as e:
            print(f"[AudioManager] Error unregister_on_speech_start: {e}")

    def unregister_on_speech_end(self, callback):
        try:
            self.tts.unregister_on_end(callback)
        except Exception as e:
            print(f"[AudioManager] Error unregister_on_speech_end: {e}")

    def speak(self, text, blocking=True, debug=False):
        """Habla texto sincronizado."""
        try:
            self.tts.speak(text, blocking=True, debug=debug)
        except Exception as e:
            print(f"[AudioManager] Error speak: {e}")

    @property
    def is_speaking(self):
        return self.tts.is_speaking

    def start_listening(self, debug=False):
        """Inicia grabación."""
        try:
            self.speech.start_recording(debug=debug)
        except Exception as e:
            print(f"[AudioManager] Error listening: {e}")

    def stop_listening(self, debug=False):
        """Detiene grabación."""
        try:
            return self.speech.stop_recording(debug=debug)
        except Exception as e:
            print(f"[AudioManager] Error stop: {e}")
            return None

    def recalibrate(self, duration=1.0):
        """Recalibra micrófono."""
        try:
            self.speech.calibrate(duration=duration)
            print(f"[AudioManager] Recalibrado ({duration}s)")
        except Exception as e:
            print(f"[AudioManager] Error recalibrar: {e}")

    # ===== RECONOCIMIENTO CON SPEAKER ID =====
    
    def recognize_with_speaker(self, audio, debug=False):
        """
        Reconoce texto Y quién lo dijo
        
        Returns:
            dict: {
                'text': str,
                'speaker': str or None,
                'confidence': float
            }
        """
        result = {
            'text': None,
            'speaker': None,
            'confidence': 0.0
        }
        
        # 1. Reconocer texto
        try:
            text = self.speech.recognize(audio, debug=debug)
            result['text'] = text
        except Exception as e:
            if debug:
                print(f"[AudioManager] Error reconociendo texto: {e}")
            return result
            
        # 2. Identificar speaker (si hay perfiles y el sistema está disponible)
        if self.speaker_system and self.speaker_system.voice_profiles:
            try:
                # Convertir audio a numpy array
                if hasattr(audio, 'get_raw_data'):
                    audio_data = np.frombuffer(
                        audio.get_raw_data(convert_rate=16000, convert_width=2),
                        dtype=np.int16
                    )
                else:
                    audio_data = audio
                    
                speaker, confidence = self.speaker_system.identify_speaker(
                    audio_data,
                    sample_rate=16000,
                    threshold=0.70  # Ajustable
                )
                
                result['speaker'] = speaker
                result['confidence'] = confidence
                
                if debug:
                    if speaker:
                        print(f"[AudioManager] 👤 Speaker: {speaker} ({confidence:.0%})")
                    else:
                        print(f"[AudioManager] 👤 Speaker desconocido (mejor: {confidence:.0%})")
                        
            except Exception as e:
                if debug:
                    print(f"[AudioManager] Error identificando speaker: {e}")
        elif debug and self.speaker_system:
            print("[AudioManager] ℹ️ No hay perfiles de voz registrados")
        
        return result
        
    def register_new_voice(self, name, audio_samples):
        """
        Registra una nueva voz
        
        Args:
            name: Nombre de la persona
            audio_samples: Lista de numpy arrays con muestras de audio
            
        Returns:
            bool: True si se registró correctamente
        """
        if not self.speaker_system:
            print("[AudioManager] ⚠️ Speaker ID no disponible")
            return False
            
        try:
            return self.speaker_system.register_voice(name, audio_samples)
        except Exception as e:
            print(f"[AudioManager] Error registrando voz: {e}")
            return False
        
    def get_registered_speakers(self):
        """
        Lista speakers registrados
        
        Returns:
            list: Lista de nombres registrados
        """
        if not self.speaker_system:
            return []
        return self.speaker_system.list_profiles()
        
    def remove_speaker(self, name):
        """
        Elimina un perfil de voz
        
        Args:
            name: Nombre del perfil a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        if not self.speaker_system:
            return False
        return self.speaker_system.remove_profile(name)


# ===== INSTANCIA GLOBAL =====
audio_manager = AudioManager()
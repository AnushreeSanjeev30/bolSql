"""
app/asr/whisper_asr.py
Whisper ASR wrapper — optimized for low-end hardware.
Records from mic, transcribes with noise tolerance.
Falls back gracefully if mic/whisper unavailable.
"""

import sys
import tempfile
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import WHISPER_MODEL, ASR_LANGUAGE, RECORD_SECONDS, SAMPLE_RATE
from logger import get_logger

log = get_logger("asr")


class WhisperASR:
    def __init__(self):
        self._model = None
        self._load_model()

    def _load_model(self):
        try:
            import whisper
            log.info("Loading Whisper model: %s (this may take a moment first time)", WHISPER_MODEL)
            self._model = whisper.load_model(WHISPER_MODEL)
            log.info("Whisper model ready")
        except ImportError:
            log.warning("openai-whisper not installed. ASR unavailable. Run: pip install openai-whisper")
        except Exception as e:
            log.error("Failed to load Whisper: %s", e)

    def record_audio(self, seconds: int = RECORD_SECONDS) -> Optional[bytes]:
        """Record from default microphone. Returns raw wav bytes or None."""
        try:
            import sounddevice as sd
            import numpy as np
            from scipy.io.wavfile import write as wav_write
            import io

            log.info("Recording for %d seconds...", seconds)
            audio = sd.rec(
                int(seconds * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16"
            )
            sd.wait()

            # Convert to wav bytes
            buf = io.BytesIO()
            wav_write(buf, SAMPLE_RATE, audio)
            return buf.getvalue()

        except ImportError:
            log.error("sounddevice/scipy not installed. Run: pip install sounddevice scipy")
            return None
        except Exception as e:
            log.error("Recording failed: %s", e)
            return None

    def transcribe_bytes(self, audio_bytes: bytes) -> Optional[str]:
        """Transcribe audio bytes using Whisper."""
        if not self._model:
            log.error("Whisper model not loaded")
            return None

        try:
            import numpy as np

            # Write to temp file (Whisper needs file path)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            result = self._model.transcribe(
                tmp_path,
                language=ASR_LANGUAGE if ASR_LANGUAGE != "auto" else None,
                task="transcribe",
                fp16=False,   # CPU-safe
                condition_on_previous_text=False,  # More robust for short commands
            )
            text = result.get("text", "").strip()
            Path(tmp_path).unlink(missing_ok=True)

            if not text:
                log.warning("Whisper returned empty transcription")
                return None

            log.info("Transcribed: '%s'", text)
            return text

        except Exception as e:
            log.error("Transcription failed: %s", e)
            return None

    def transcribe_file(self, file_path: str) -> Optional[str]:
        """Transcribe from an audio file path."""
        if not self._model:
            return None
        try:
            result = self._model.transcribe(
                file_path,
                language=ASR_LANGUAGE if ASR_LANGUAGE != "auto" else None,
                fp16=False,
            )
            return result.get("text", "").strip() or None
        except Exception as e:
            log.error("File transcription failed: %s", e)
            return None

    def record_and_transcribe(self, seconds: int = RECORD_SECONDS) -> Optional[str]:
        """Full pipeline: record → transcribe. Returns text or None."""
        audio = self.record_audio(seconds)
        if not audio:
            return None
        return self.transcribe_bytes(audio)

    @property
    def available(self) -> bool:
        return self._model is not None


_asr: Optional[WhisperASR] = None


def get_asr() -> WhisperASR:
    global _asr
    if _asr is None:
        _asr = WhisperASR()
    return _asr

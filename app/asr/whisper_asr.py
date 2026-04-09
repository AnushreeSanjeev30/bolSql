"""
app/asr/whisper_asr.py
Sarvam Saaras v3 ASR wrapper — native Hinglish support.
Records from mic, transcribes with codemix mode for natural Hinglish output.
Falls back gracefully if mic/Sarvam API unavailable.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import RECORD_SECONDS, SAMPLE_RATE
from logger import get_logger

log = get_logger("asr")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_URL = "https://api.sarvam.ai/speech-to-text"


class WhisperASR:
    """ASR interface using Sarvam Saaras v3 API."""

    def __init__(self):
        if not SARVAM_API_KEY or SARVAM_API_KEY == "your_key_here":
            log.warning("SARVAM_API_KEY not set in .env — ASR will fail. Set it to use Sarvam.")
            self._available = False
        else:
            self._available = True
            log.info("Sarvam Saaras v3 ASR initialized")

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

    def transcribe_bytes(self, audio_bytes: bytes) -> Optional[Tuple[str, float]]:
        """
        Transcribe audio bytes using Sarvam Saaras v3.
        
        Args:
            audio_bytes: Raw audio bytes (WAV format)
        
        Returns:
            Tuple of (transcribed_text, confidence) or None on failure.
            confidence: 0.0-1.0 score (Sarvam doesn't return per-segment confidence,
                                      so we return 0.9 for successful transcription)
        """
        if not self._available:
            log.error("Sarvam API key not configured")
            return None

        try:
            # Write to temp file (Sarvam needs file to read)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            with open(tmp_path, "rb") as f:
                files = {"file": (Path(tmp_path).name, f, "audio/wav")}
                headers = {"api-subscription-key": SARVAM_API_KEY}
                data = {
                    "model": "saaras:v3",
                    "mode": "codemix",        # KEY: Hinglish output with native script
                    "language_code": "hi-IN",
                }

                response = requests.post(
                    SARVAM_URL,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30,
                )

            response.raise_for_status()
            result = response.json()
            text = result.get("transcript", "").strip()
            Path(tmp_path).unlink(missing_ok=True)

            if not text:
                log.warning("Sarvam returned empty transcription")
                return None

            # Sarvam doesn't return per-segment confidence, so use 0.9 for successful transcription
            confidence = 0.9
            log.info("Transcribed: '%s' (Sarvam codemix)", text)
            return (text, confidence)

        except requests.exceptions.RequestException as e:
            log.error("Sarvam API error: %s", e)
            return None
        except Exception as e:
            log.error("Transcription failed: %s", e)
            return None

    def transcribe_file(self, file_path: str) -> Optional[Tuple[str, float]]:
        """
        Transcribe from an audio file path using Sarvam.
        
        Returns:
            Tuple of (transcribed_text, confidence) or None on failure.
        """
        if not self._available:
            return None

        try:
            with open(file_path, "rb") as f:
                files = {"file": (Path(file_path).name, f, "audio/wav")}
                headers = {"api-subscription-key": SARVAM_API_KEY}
                data = {
                    "model": "saaras:v3",
                    "mode": "codemix",
                    "language_code": "hi-IN",
                }

                response = requests.post(
                    SARVAM_URL,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30,
                )

            response.raise_for_status()
            result = response.json()
            text = result.get("transcript", "").strip()

            return (text, 0.9) if text else None

        except requests.exceptions.RequestException as e:
            log.error("Sarvam file transcription error: %s", e)
            return None
        except Exception as e:
            log.error("File transcription failed: %s", e)
            return None

    def record_and_transcribe(self, seconds: int = RECORD_SECONDS) -> Optional[Tuple[str, float]]:
        """Full pipeline: record → transcribe. Returns (text, confidence) or None."""
        audio = self.record_audio(seconds)
        if not audio:
            return None
        return self.transcribe_bytes(audio)

    @property
    def available(self) -> bool:
        return self._available


_asr: Optional[WhisperASR] = None


def get_asr() -> WhisperASR:
    global _asr
    if _asr is None:
        _asr = WhisperASR()
    return _asr

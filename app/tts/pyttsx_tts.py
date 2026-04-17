"""
app/tts/pyttsx_tts.py
Text-to-Speech using pyttsx3 — free, offline, works on macOS/Linux/Windows.
Supports both Hindi and English.
"""

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import get_logger

log = get_logger("tts")


class Pyttsx3TTS:
    """Text-to-Speech interface using pyttsx3."""

    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self._available = True
            
            # Optimize for Hindi/Hinglish
            self.engine.setProperty('rate', 150)  # Slower for clarity
            self.engine.setProperty('volume', 0.9)
            
            log.info("pyttsx3 TTS initialized")
        except ImportError:
            log.warning("pyttsx3 not installed. Run: pip install pyttsx3")
            self._available = False
            self.engine = None
        except Exception as e:
            log.warning(f"pyttsx3 initialization failed: {e}")
            self._available = False
            self.engine = None

    @property
    def available(self) -> bool:
        return self._available

    def speak(self, text: str, language: str = "hinglish") -> bool:
        """
        Speak text aloud using system TTS.
        
        Args:
            text: Text to speak (supports Hindi/English/Hinglish/Tamil)
            language: "hinglish", "hindi", or "tamil" (default: "hinglish")
        
        Returns:
            True if successful, False otherwise
        """
        if not self._available or not self.engine:
            log.error("TTS engine not available")
            return False

        try:
            # pyttsx3 automatically detects language from Unicode characters
            # (Tamil script ஆ, Hindi script आ, etc.)
            self.engine.say(text)
            self.engine.runAndWait()
            log.info(f"TTS spoke ({language}): {text[:50]}...")
            return True
        except Exception as e:
            log.error(f"TTS speak failed: {e}")
            return False

    def speak_async(self, text: str, language: str = "hinglish") -> bool:
        """
        Speak text asynchronously (starts and returns immediately).
        
        Args:
            text: Text to speak
            language: "hinglish", "hindi", or "tamil" (default: "hinglish")
        
        Returns:
            True if queued successfully, False otherwise
        """
        if not self._available or not self.engine:
            return False

        try:
            self.engine.say(text)
            # Don't wait — caller can choose to wait or continue
            return True
        except Exception as e:
            log.error(f"TTS async speak failed: {e}")
            return False


def get_tts() -> Optional[Pyttsx3TTS]:
    """Get or create TTS engine singleton."""
    if not hasattr(get_tts, "_instance"):
        get_tts._instance = Pyttsx3TTS()
    return get_tts._instance

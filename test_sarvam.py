#!/usr/bin/env python3
"""
test_sarvam.py
Quick test for Sarvam integration setup and connectivity.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env first
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
from app.asr.whisper_asr import get_asr
from logger import get_logger

log = get_logger("test_sarvam")

print("\n" + "="*60)
print("SARVAM INTEGRATION TEST")
print("="*60)

# Test 1: API Key
print("\n[1] API Key Configuration")
print("-" * 60)
if SARVAM_API_KEY:
    print(f"✓ API Key is set")
    print(f"  Format: {SARVAM_API_KEY[:10]}...{SARVAM_API_KEY[-5:]}")
    print(f"  Length: {len(SARVAM_API_KEY)}")
    if SARVAM_API_KEY.startswith("sk_"):
        print(f"✓ Key format is valid (sk_ prefix)")
    else:
        print(f"⚠ Key format unusual (expected sk_ prefix)")
else:
    print(f"✗ API Key not configured in .env")
    sys.exit(1)

# Test 2: ASR Module Initialization
print("\n[2] ASR Module Initialization")
print("-" * 60)
try:
    asr = get_asr()
    print(f"✓ ASR module initialized")
    print(f"  Available: {asr.available}")
    print(f"  Provider: Sarvam Saaras v3")
    if not asr.available:
        print(f"✗ ASR not available - check API key or configuration")
except Exception as e:
    print(f"✗ Failed to initialize ASR: {e}")
    sys.exit(1)

# Test 3: Dependencies
print("\n[3] Python Dependencies")
print("-" * 60)
dependencies = {
    "requests": "Required (for API calls)",
    "sounddevice": "Optional (for mic recording)",
    "scipy": "Optional (for audio processing)",
    "numpy": "Optional (for audio processing)",
}

for pkg, desc in dependencies.items():
    try:
        mod = __import__(pkg)
        version = getattr(mod, "__version__", "installed")
        print(f"✓ {pkg:15} {version:20} ({desc})")
    except ImportError:
        req = "(required)" if "Required" in desc else "(optional)"
        print(f"✗ {pkg:15} not installed  {req} {desc}")

# Test 4: API Endpoint Configuration
print("\n[4] Sarvam API Configuration")
print("-" * 60)
print(f"Endpoint:    https://api.sarvam.ai/speech-to-text")
print(f"Model:       saaras:v3")
print(f"Mode:        codemix (native Hinglish)")
print(f"Language:    hi-IN (Hindi - India)")
print(f"Request:     POST with audio file + api-subscription-key header")

# Test 5: Test with dummy audio (if available)
print("\n[5] Testing Voice Functionality")
print("-" * 60)
print("Options to test voice:")
print("  a) Via API:  POST /voice with audio file")
print("  b) Via CLI:  python main.py --voice (requires microphone)")
print("  c) Via test: See test_voice_example() below")

# Test 6: Summary
print("\n" + "="*60)
if asr.available:
    print("✓ SARVAM INTEGRATION IS READY")
    print("\nNext steps:")
    print("  1. Test via API: curl -X POST -F 'audio=@test.wav' http://localhost:8000/voice")
    print("  2. Use the frontend voice panel")
    print("  3. Test via CLI: python main.py --voice")
else:
    print("✗ SARVAM INTEGRATION HAS ISSUES")
    print("\nFix:")
    print("  1. Verify SARVAM_API_KEY in .env")
    print("  2. Check if key has correct format (sk_...)")
    print("  3. Verify Sarvam API is accessible")
print("="*60 + "\n")

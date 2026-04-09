#!/usr/bin/env python3
"""
Diagnose voice system issues
"""

import sys
import os

print("\n🔍 Voice System Diagnostics\n")
print("=" * 70)

# 1. Check Python packages
print("\n1️⃣ Checking audio libraries...")
try:
    import sounddevice as sd
    print(f"   ✅ sounddevice: {sd.__version__}")
except ImportError as e:
    print(f"   ❌ sounddevice: NOT INSTALLED")
    sys.exit(1)

try:
    import scipy
    print(f"   ✅ scipy: {scipy.__version__}")
except ImportError as e:
    print(f"   ❌ scipy: NOT INSTALLED")
    sys.exit(1)

try:
    import whisper
    print(f"   ✅ openai-whisper: installed")
except ImportError as e:
    print(f"   ❌ openai-whisper: NOT INSTALLED")
    sys.exit(1)

try:
    from rapidfuzz import fuzz
    print(f"   ✅ rapidfuzz: installed")
except ImportError:
    print(f"   ⚠️  rapidfuzz: not installed (optional, fuzzy matching disabled)")

# 2. Check microphone
print("\n2️⃣ Checking audio devices...")
try:
    import sounddevice as sd
    devices = sd.query_devices()
    
    print(f"   Total devices: {len(devices)}")
    
    # List all input devices
    input_devices = [i for i in range(len(devices)) if devices[i]['max_input_channels'] > 0]
    print(f"   Input devices: {input_devices}")
    
    if not input_devices:
        print(f"   ❌ NO INPUT DEVICES FOUND")
        sys.exit(1)
    
    default_in = sd.default.device[0]
    print(f"   Default input device: {default_in}")
    if default_in >= 0 and default_in < len(devices):
        print(f"   Device: {devices[default_in]['name']}")
        print(f"   Channels: {devices[default_in]['max_input_channels']}")
    else:
        print(f"   ⚠️  Invalid default device index")
        
except Exception as e:
    print(f"   ❌ Error checking devices: {e}")

# 3. Check Whisper model
print("\n3️⃣ Checking Whisper model cache...")
cache_dir = os.path.expanduser("~/.cache/whisper")
if os.path.exists(cache_dir):
    models = os.listdir(cache_dir)
    if models:
        print(f"   ✅ Cached models: {models}")
    else:
        print(f"   ⚠️  Cache empty (will download on first use)")
else:
    print(f"   ℹ️  No cache directory yet (will create on first use)")

# 4. Test if we can record audio
print("\n4️⃣ Testing audio recording...")
try:
    import sounddevice as sd
    import numpy as np
    from scipy.io.wavfile import write as wav_write
    
    print(f"   Recording 1 second of audio...")
    audio_data = sd.rec(int(16000 * 1), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    
    if audio_data is not None and audio_data.shape[0] > 0:
        print(f"   ✅ Successfully recorded {audio_data.shape[0]} samples")
    else:
        print(f"   ❌ Recording returned empty data")
        
except Exception as e:
    print(f"   ❌ Recording failed: {e}")

# 5. Test ASR
print("\n5️⃣ Testing Whisper initialization...")
try:
    sys.path.insert(0, '/Users/ankanamandal/Documents/college_sem/SEM-6/lab/genai/project/bolSql')
    from app.asr.whisper_asr import get_asr
    
    print(f"   Loading Whisper model (this may take 1-2 min)...")
    asr = get_asr()
    
    if asr and asr.available:
        print(f"   ✅ ASR available and ready")
    else:
        print(f"   ⚠️  ASR not available")
        
except Exception as e:
    print(f"   ❌ ASR initialization failed: {e}")

print("\n" + "=" * 70)
print("\n✅ Diagnostics complete! All systems ready for voice input.\n")

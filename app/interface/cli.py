"""
app/interface/cli.py
CLI experience — smooth, colored, shopkeeper-friendly terminal UI.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import get_logger

log = get_logger("cli")

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class _Stub:
        def __getattr__(self, _): return ""
    Fore = Style = _Stub()

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


def _c(color, text):
    return f"{color}{text}{Style.RESET_ALL}" if HAS_COLOR else text


def print_header(voice_output_enabled=False):
    print()
    print(_c(Fore.CYAN, "━" * 50))
    print(_c(Fore.CYAN, "  🏪 VoiceSQL — Kirana Intelligence"))
    print(_c(Fore.CYAN, "  आपकी दुकान का AI सहायक"))
    print(_c(Fore.CYAN, "━" * 50))
    print(_c(Fore.YELLOW, "  Commands:"))
    print("    /voice  — mic se bolo (Whisper ASR)")
    print("    /speak  — voice output toggle" + (_c(Fore.GREEN, " ✓") if voice_output_enabled else ""))
    print("    /list   — sab items dikhao")
    print("    /help   — help dekho")
    print("    /quit   — band karo")
    print(_c(Fore.CYAN, "━" * 50))
    print()


def print_help():
    print()
    print(_c(Fore.YELLOW, "📖 Kaise use karein:"))
    print()
    print("  ADD (stock badhana):")
    print("    50kg atta add karo")
    print("    20 litre tel daal do")
    print()
    print("  SELL (sale record karna):")
    print("    10 packet biscuit becha")
    print("    2kg atta gaya")
    print()
    print("  QUERY (stock check karna):")
    print("    chawal kitna bacha hai")
    print("    sab items ki list dikhao")
    print()


def print_result(result, verbose=False, tts=None):
    print()
    if result.success:
        print(_c(Fore.GREEN, f"✅  {result.response}"))
    else:
        print(_c(Fore.RED, f"❌  {result.response}"))
    
    # Speak response if TTS enabled
    if tts and tts.available:
        try:
            tts.speak(result.response)
        except Exception as e:
            log.debug(f"TTS failed: {e}")
    
    if verbose and result.sql:
        print(_c(Fore.CYAN, f"   SQL: {result.sql}"))
    if verbose and result.db_rows and len(result.db_rows) > 1:
        _print_table(result.db_rows)
    print()


def _print_table(rows):
    if not rows:
        return
    if HAS_TABULATE:
        print(_c(Fore.CYAN, tabulate(rows, headers="keys", tablefmt="rounded_outline")))
    else:
        keys = list(rows[0].keys())
        print("  " + " | ".join(keys))
        print("  " + "-" * 40)
        for row in rows:
            print("  " + " | ".join(str(row.get(k, "")) for k in keys))


def run_cli(voice_mode=False, verbose=False):
    from pipeline import process
    from app.db.database import init_db

    init_db()
    
    # Initialize TTS (always try, even if voice_mode is off)
    tts = None
    try:
        from app.tts.pyttsx_tts import get_tts
        tts = get_tts()
    except Exception as e:
        log.debug(f"TTS initialization failed: {e}")
    
    voice_output_enabled = False
    print_header(voice_output_enabled=voice_output_enabled)

    asr = None
    if voice_mode:
        try:
            from app.asr.whisper_asr import get_asr
            asr = get_asr()
            if asr.available:
                print(_c(Fore.GREEN, "🎤 Whisper ASR ready\n"))
            else:
                print(_c(Fore.YELLOW, "⚠️  Whisper not available — text mode only\n"))
                asr = None
        except Exception as e:
            print(_c(Fore.YELLOW, f"⚠️  ASR error: {e} — text mode only\n"))
            asr = None

    while True:
        try:
            prompt = _c(Fore.YELLOW, "बोलिए > ")
            user_input = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print(_c(Fore.CYAN, "\n\nDhanyavaad! Phir milenge. 🙏"))
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/q", "/exit", "quit", "exit"):
            print(_c(Fore.CYAN, "\nDhanyavaad! Phir milenge. 🙏"))
            break

        if user_input.lower() in ("/help", "/h"):
            print_help()
            continue

        if user_input.lower() in ("/list", "/l"):
            result = process("sab items ki list dikhao")
            print_result(result, verbose=verbose, tts=tts if voice_output_enabled else None)
            if result.db_rows and len(result.db_rows) > 1:
                _print_table(result.db_rows)
            continue

        if user_input.lower() in ("/speak", "/s"):
            if tts and tts.available:
                voice_output_enabled = not voice_output_enabled
                status = _c(Fore.GREEN, "🔊 ON") if voice_output_enabled else _c(Fore.YELLOW, "🔇 OFF")
                print(_c(Fore.CYAN, f"\nVoice output: {status}\n"))
                print_header(voice_output_enabled=voice_output_enabled)
            else:
                print(_c(Fore.YELLOW, "\n⚠️  TTS not available\n"))
            continue

        if user_input.lower() in ("/voice", "/v") and asr:
            print(_c(Fore.CYAN, "\n🎤 Recording... (speak now)"))
            result = asr.record_and_transcribe()
            if result:
                text, confidence = result
                print(_c(Fore.GREEN, f"   Suna: \"{text}\" (confidence: {confidence:.1%})"))
                
                # Confidence threshold: reject low-confidence transcriptions
                if confidence < 0.5:
                    print(_c(Fore.YELLOW, "   ⚠️  Confidence low. Dobara try karein.\n"))
                    continue
                
                result = process(text, is_voice=True)
            else:
                print(_c(Fore.RED, "   Kuch samajh nahi aaya. Dobara try karein.\n"))
                continue
        else:
            print(_c(Fore.CYAN, "🧠 Processing..."))
            t0 = time.time()
            result = process(user_input)
            elapsed = time.time() - t0
            log.debug("Pipeline took %.2fs", elapsed)

        print_result(result, verbose=verbose, tts=tts if voice_output_enabled else None)

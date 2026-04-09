# cd /Users/bhavana/Downloads/final_voicesql/frontend
# npm install
# npm run build"""
# main.py — VoiceSQL entry point.

# Usage:
#     python main.py              # Text mode (default)
#     python main.py --voice      # Voice mode (Whisper ASR)
#     python main.py --verbose    # Show SQL in output
#     python main.py --api        # Start FastAPI server (optional)
#     python main.py --test       # Run self-test suite
# """

import argparse
import sys
from pathlib import Path

from config import DB_PATH

sys.path.insert(0, str(Path(__file__).parent))

# Initialize database first
from app.db.database import init_db
init_db()

# Then run migrations and analytics
from app.db.migrations import run_customer_migrations
from app.trends.customer_engine import save_rfm_to_db, save_predictions_to_db

run_customer_migrations(DB_PATH)
save_rfm_to_db(DB_PATH)
save_predictions_to_db(DB_PATH)

def run_tests():
    from app.db.database import init_db
    from pipeline import process

    init_db()

    test_cases = [
        ("50kg atta add karo",           "ADD",   True),
        ("20 litre tel daal do",         "ADD",   True),
        ("10 packet biscuit enter karo", "ADD",   True),
        ("chawal kitna bacha hai",       "QUERY", True),
        ("atta check karo",              "QUERY", True),
        ("sab items ki list dikhao",     "QUERY", True),
        ("5kg dal becha",                "SELL",  True),
        ("2 litre doodh gaya",           "SELL",  True),
    ]

    from app.trends.classifier import detect_language
    print("\n🧪 Running pipeline self-tests...\n")
    passed = 0
    for query, expected_intent, should_succeed in test_cases:
        lang = detect_language(query)
        result = process(query, language=lang)
        ok = result.success == should_succeed
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} [{result.intent or '?':5s}] {query[:45]:45s}  →  {result.response[:50]}")

    print(f"\n  {passed}/{len(test_cases)} tests passed\n")


def run_api():
    try:
        import uvicorn
        from api import app as fastapi_app
        print("\n🌐 Starting FastAPI server on http://0.0.0.0:8000\n")
        uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, reload=False)
    except ImportError:
        print("FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="VoiceSQL — Hinglish voice inventory for kirana stores"
    )
    parser.add_argument("--voice",   action="store_true", help="Enable Whisper ASR voice input")
    parser.add_argument("--verbose", action="store_true", help="Show generated SQL queries")
    parser.add_argument("--test",    action="store_true", help="Run self-test suite and exit")
    parser.add_argument("--api",     action="store_true", help="Start FastAPI REST server")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    if args.api:
        run_api()
        return

    from app.interface.cli import run_cli
    run_cli(voice_mode=args.voice, verbose=args.verbose)


if __name__ == "__main__":
    main()

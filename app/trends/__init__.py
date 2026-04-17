"""
VoiceSQL Trends Module
======================
13 analytical trend engines for Kirana Intelligence.

Usage:
    from app.trends import TrendsPipeline
    pipeline = TrendsPipeline(db_path="kirana.db")
    response = pipeline.process("pichle 7 din ka sales batao")
    print(response)
"""

from .engine import TrendsEngine
from .classifier import classify_trend
from .formatter import format_trend_response


class TrendsPipeline:
    """
    Single entry point for the full trends pipeline.
    Plug this into your existing pipeline.py.
    """

    def __init__(self, db_path: str = "kirana.db"):
        self.db_path = db_path
        self.engine = TrendsEngine(db_path)

    def is_trend_query(self, query: str) -> bool:
        """Quick check: does this query want a trend analysis?"""
        trend_type, _ = classify_trend(query)
        return trend_type is not None

    def process(self, query: str, language: str = "hinglish") -> str:
        """
        Full pipeline:
          query → classify → engine → format → language-appropriate response
        """
        trend_type, params = classify_trend(query)
        if not trend_type:
            return None  # Not a trend query, let main pipeline handle it

        # Monthly report is handled separately (not via engine)
        if trend_type == "monthly_report":
            from .monthly_report import generate_monthly_report, _render_text
            import re
            from datetime import date
            # Allow "2025 3" style month override in the query
            m = re.search(r"(\d{4})\D+(\d{1,2})", query)
            if m:
                year, month = int(m.group(1)), int(m.group(2))
            else:
                today = date.today()
                year  = today.year if today.month > 1 else today.year - 1
                month = today.month - 1 if today.month > 1 else 12
            report = generate_monthly_report(self.db_path, year, month)
            return _render_text(report)

        raw = self.engine.dispatch(trend_type, params)
        return format_trend_response(trend_type, raw, language=language)


__all__ = ["TrendsEngine", "TrendsPipeline", "classify_trend", "format_trend_response"]

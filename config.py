"""
config.py — Central configuration for Restaurant Spy.
Loads from .env and exposes typed settings across the project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent / ".env")


class Config:
    # --- Paths ---
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    REPORTS_DIR = BASE_DIR / "reports"
    STATIC_DIR = BASE_DIR / "static"

    # --- API Keys ---
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")

    # --- WhatsApp / Twilio (Phase 2) ---
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    META_WHATSAPP_TOKEN: str = os.getenv("META_WHATSAPP_TOKEN", "")
    META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")
    WEBHOOK_VERIFY_TOKEN: str = os.getenv("WEBHOOK_VERIFY_TOKEN", "restaurant_spy_secret")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/restaurant_spy.db")

    # --- App Settings ---
    APP_NAME: str = os.getenv("APP_NAME", "Restaurant Spy")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Polite scraping delays (seconds)
    SCRAPE_DELAY_MIN: int = int(os.getenv("SCRAPE_DELAY_MIN", "8"))
    SCRAPE_DELAY_MAX: int = int(os.getenv("SCRAPE_DELAY_MAX", "12"))

    # Scheduler
    WEEKLY_BRIEF_DAY: str = os.getenv("WEEKLY_BRIEF_DAY", "monday")
    WEEKLY_BRIEF_HOUR: int = int(os.getenv("WEEKLY_BRIEF_HOUR", "8"))

    # --- Intelligence Thresholds ---
    # Red Alert: price change % that triggers an immediate alert
    PRICE_ALERT_THRESHOLD: float = 0.10  # 10%
    # Red Alert: number of negative reviews in 24h
    NEGATIVE_REVIEW_ALERT_COUNT: int = 3
    # Opportunity: sentiment drop vs last week that triggers a suggestion
    SENTIMENT_DROP_THRESHOLD: float = 0.3

    # --- Claude Model ---
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096

    # --- Competitor limits per tier ---
    TIER_LIMITS = {
        "essential": 3,
        "pro": 5,
        "dominator": 10,
    }

    @classmethod
    def ensure_dirs(cls):
        """Create all required directories if they don't exist."""
        for d in [cls.DATA_DIR, cls.LOGS_DIR, cls.REPORTS_DIR, cls.STATIC_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing critical env vars (empty = all good)."""
        missing = []
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not cls.FIRECRAWL_API_KEY:
            missing.append("FIRECRAWL_API_KEY")
        return missing


config = Config()
config.ensure_dirs()

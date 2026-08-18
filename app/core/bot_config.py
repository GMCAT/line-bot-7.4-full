import os


DEFAULT_SERVICES = {
    "news",
    "stocks",
    "ai_chat",
    "contacts",
    "subscriptions",
    "admin",
    "settings",
}


def enabled_services(bot_id: str = "default") -> set[str]:
    """รองรับรายบอท เช่น BOT_SERVICES_NEWS_BOT=news,stocks"""
    key = "BOT_SERVICES_" + bot_id.upper().replace("-", "_")
    raw = os.getenv(key) or os.getenv("BOT_SERVICES", ",".join(sorted(DEFAULT_SERVICES)))
    return {item.strip() for item in raw.split(",") if item.strip()}

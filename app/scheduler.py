import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import storage, news, line_client


def _looks_like_ticker(topic: str) -> str | None:
    """เดาว่าหัวข้อที่ติดตามเป็นสัญลักษณ์หุ้นหรือไม่ (คำเดียว ตัวพิมพ์ใหญ่ อาจมี .BK ต่อท้าย)"""
    candidate = topic.strip().upper().replace(" ", "")
    if 1 <= len(candidate) <= 12 and all(c.isalnum() or c in ".-" for c in candidate):
        # หัวข้อที่มีช่องว่าง/เป็นประโยคยาว ๆ ไม่นับเป็น ticker
        if " " not in topic.strip():
            return candidate
    return None


def send_daily_digest() -> None:
    for chat_id, chat in storage.all_chats().items():
        if not chat.get("subscribed_daily"):
            continue

        parts = []

        # 1) ข่าวเด่นทั่วไปประจำวัน
        general = news.fetch_headlines(query=None, limit=5)
        parts.append(news.format_plain("ข่าวเด่นวันนี้", general))

        # 2) หัวข้อที่ผู้ใช้ติดตามไว้
        for topic in chat.get("topics", []):
            ticker = _looks_like_ticker(topic)
            if ticker:
                parts.append(news.get_stock_price(ticker))
            else:
                items = news.fetch_headlines(query=topic, limit=3)
                parts.append(news.format_plain(f"ติดตาม: {topic}", items))

        message = "\n\n".join(parts)
        try:
            line_client.push_text(chat_id, message)
        except Exception as e:
            print(f"[scheduler] ส่งข้อความไปที่ {chat_id} ไม่สำเร็จ: {e}")


def start_scheduler() -> BackgroundScheduler:
    hour = int(os.getenv("DAILY_DIGEST_HOUR", "8"))
    minute = int(os.getenv("DAILY_DIGEST_MINUTE", "0"))

    scheduler = BackgroundScheduler(timezone="Asia/Bangkok")
    scheduler.add_job(
        send_daily_digest,
        CronTrigger(hour=hour, minute=minute),
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler

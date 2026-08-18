"""ระบบข่าวจาก Google News RSS จัดรูปแบบด้วย Python และไม่เรียก AI"""
import urllib.parse


def fetch_headlines(query: str | None = None, limit: int = 5) -> list[dict]:
    """
    ดึงหัวข้อข่าวจาก Google News RSS
    query=None -> ข่าวเด่นทั่วไป (ประเทศไทย)
    query="คำค้น" -> ข่าวตามคำค้นนั้น
    """
    import feedparser

    if query:
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=th&gl=TH&ceid=TH:th"
    else:
        url = "https://news.google.com/rss?hl=th&gl=TH&ceid=TH:th"

    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "") if hasattr(entry, "source") else "",
        })
    return items


def _format_plain(topic_label: str, headlines: list[dict]) -> str:
    """โหมดฟรี 100% — จัดรูปแบบข่าวด้วย Python ธรรมดา ไม่พึ่ง AI เลย"""
    lines = [f"🗞️ {topic_label}"]
    for h in headlines:
        source = f" ({h['source']})" if h["source"] else ""
        lines.append(f"• {h['title']}{source}\n  {h['link']}")
    return "\n".join(lines)


def format_plain(topic_label: str, headlines: list[dict]) -> str:
    """Public interface สำหรับ News Service; ไม่เรียก AI"""
    if not headlines:
        return f"ไม่พบข่าวล่าสุดเกี่ยวกับ \"{topic_label}\" ครับ"
    return _format_plain(topic_label, headlines)


def get_stock_price(ticker: str) -> str:
    """
    ดึงราคาหุ้นล่าสุดด้วย yfinance (ฟรี ไม่ต้องใช้ API key)
    ticker เช่น AAPL, PTT.BK, DELTA.BK
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = info.get("last_price")
        prev_close = info.get("previous_close")
        if price is None:
            return f"ไม่พบข้อมูลราคาหุ้นของ \"{ticker}\" ครับ ลองตรวจสอบสัญลักษณ์หุ้นอีกครั้ง"
        change = price - prev_close if prev_close else 0
        pct = (change / prev_close * 100) if prev_close else 0
        arrow = "🔺" if change > 0 else ("🔻" if change < 0 else "➖")
        return f"📈 {ticker}: {price:,.2f} {arrow} {change:+.2f} ({pct:+.2f}%)"
    except Exception as e:
        return f"ดึงราคาหุ้น \"{ticker}\" ไม่สำเร็จ: {e}"

import os
from dotenv import load_dotenv

load_dotenv()  # โหลดค่าจาก .env ก่อน import โมดูลอื่นที่ต้องใช้ env vars

from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    JoinEvent,
    LeaveEvent,
)

from app import storage, news, line_client, db
from app.core.bot_config import enabled_services
from app.core.contracts import ServiceRequest
from app.scheduler import start_scheduler
from app.services import build_registry

app = FastAPI(title="LINE News Assistant")
parser = WebhookParser(os.environ["LINE_CHANNEL_SECRET"])
service_registry = build_registry()

CONTACT_TYPE_LABEL = {
    "GENERAL": "ทั่วไป", "EMERGENCY": "ฉุกเฉิน", "MAINTENANCE": "ซ่อมบำรุง",
    "IT_SUPPORT": "IT", "LAB_SUPPORT": "แล็บ", "VENDOR": "ผู้ขาย/ผู้จำหน่าย", "OTHER": "อื่น ๆ",
}
CONTACT_TYPE_BY_LABEL = {v: k for k, v in CONTACT_TYPE_LABEL.items()}
CONTACT_ROLE_BY_LABEL = {"หลัก": "PRIMARY", "สำรอง": "SECONDARY"}
TRUE_WORDS = {"ใช่", "ได้", "yes", "true", "1"}

ADD_CONTACT_FORMAT_HELP = (
    "รูปแบบคำสั่งเพิ่มผู้ติดต่อ (พิมพ์หลายบรรทัดในข้อความเดียว ขึ้นบรรทัดใหม่ด้วย Shift+Enter):\n\n"
    "เพิ่มติดต่อ\n"
    "ชื่อ: นายเอ\n"
    "หน่วยงาน: กรมป่าไม้\n"
    "ตัวย่อหน่วยงาน: RFD\n"
    "ตำแหน่ง: หัวหน้าฝ่าย\n"
    "เบอร์: 0812345678\n"
    "อีเมล: a@example.com\n"
    "ไลน์: nai_a\n"
    "ประเภท: ทั่วไป\n"
    "บทบาท: หลัก\n"
    "24ชม: ไม่\n"
    "หมายเหตุ: -\n\n"
    "บังคับ: ชื่อ, หน่วยงาน (ตัวย่อไม่บังคับ และหน่วยงานใหม่จะถูกสร้างให้อัตโนมัติ)\n"
    f"ประเภท เลือกได้: {', '.join(CONTACT_TYPE_LABEL.values())}\n"
    "บทบาท เลือกได้: หลัก, สำรอง\n"
    "ฟิลด์ที่ไม่ใส่ หรือใส่ \"-\" จะเว้นว่างไว้"
)

HELP_TEXT = (
    "🤖 คำสั่งที่ใช้ได้:\n"
    "• ข่าว → ดูข่าวเด่นตอนนี้\n"
    "• หา <คำค้น> → ค้นข่าวเรื่องนั้นตอนนี้ เช่น \"หา ราคาน้ำมัน\"\n"
    "• หุ้น <สัญลักษณ์> → ราคาหุ้นล่าสุด เช่น \"หุ้น AAPL\" หรือ \"หุ้น PTT.BK\"\n"
    "• ถาม <คำถาม> → ถาม AI ทั่วไป เช่น \"ถาม Python คืออะไร\" (แยกจากระบบข่าว)\n"
    "• ติดต่อ <ชื่อ/เบอร์/อีเมล/หน่วยงาน/ตัวย่อ> → ค้นข้อมูลติดต่อ ถ้าตรงชื่อหน่วยงานจะโชว์คนทั้งหน่วยงานเลย พิมพ์ผิดเล็กน้อยก็ยังหาเจอ\n"
    "• ติดต่อฉุกเฉิน → ดูรายชื่อผู้ติดต่อฉุกเฉินทั้งหมด\n"
    "• ติดตาม <หัวข้อ/สัญลักษณ์หุ้น> → เพิ่มรายการที่จะรายงานให้ทุกวัน\n"
    "• เลิกติดตาม <หัวข้อ> → เอาออกจากรายการ\n"
    "• รายการติดตาม → ดูสิ่งที่ติดตามอยู่\n"
    "• เปิดข่าวประจำวัน / ปิดข่าวประจำวัน → เปิด-ปิดสรุปข่าวรายวัน\n"
    "• โหมด → ดูโหมด AI ถามตอบตอนนี้\n"
    "• โหมด <none/local/gemini/anthropic> → เลือก AI สำหรับคำสั่ง ถาม\n"
    "• ช่วยเหลือ → แสดงข้อความนี้\n"
    "\n"
    "🔐 คำสั่งแอดมิน:\n"
    "• เพิ่มติดต่อ → เพิ่มผู้ติดต่อใหม่ลงฐานข้อมูล (พิมพ์ \"เพิ่มติดต่อ\" เฉย ๆ เพื่อดูฟอร์แมต)\n"
    "• ข้อมูลทั้งหมด → ดึงข้อมูลผู้ติดต่อทั้งหมดจากฐานหลัก\n"
    "• ตรวจฐานข้อมูล → ตรวจการเชื่อมต่อและจำนวนข้อมูลในฐานหลัก\n"
    "\n"
    "💡 ในกลุ่ม พิมพ์ \"บอท\" หรือ \"!\" นำหน้าคำสั่งทุกครั้งถึงจะตอบ เช่น \"บอท ข่าว\" หรือ \"!ข่าว\" (หรือแท็กชื่อบอทก็ได้ถ้าระบบรองรับ)"
)


def _get_chat_id(event: MessageEvent | JoinEvent) -> tuple[str, str]:
    source = event.source
    if source.type == "group":
        return source.group_id, "group"
    if source.type == "room":
        return source.room_id, "room"
    return source.user_id, "user"


def _is_admin(user_id: str | None) -> bool:
    """
    เช็คสิทธิ์แอดมินจาก LINE user id เทียบกับ LINE_ADMIN_USER_IDS (คั่นด้วย comma ใน .env)
    ถ้ายังไม่ตั้งค่าเลย (list ว่าง) จะอนุญาตให้ทุกคนใช้ได้ไปก่อน กันใช้งานไม่ได้ตั้งแต่แรก
    แนะนำให้ไปตั้งค่าจำกัดสิทธิ์ทันทีที่รู้ user id ตัวเอง (ดู README)
    """
    admin_ids = [uid.strip() for uid in os.getenv("LINE_ADMIN_USER_IDS", "").split(",") if uid.strip()]
    if not admin_ids:
        return True
    return user_id in admin_ids


def _extract_self_mention(message: TextMessageContent) -> tuple[bool, str]:
    """
    เช็คว่าข้อความนี้แท็กบอทตัวเองไหม (ใช้เฉพาะในกลุ่ม/ห้องแชทหลายคน)
    คืนค่า (ถูกแท็กบอทไหม, ข้อความหลังตัดส่วนที่เป็นแท็กบอทออกแล้ว)
    LINE ส่ง is_self=True มาให้เลยถ้า mention นั้นคือบอทเจ้าของ channel เอง
    ไม่ต้องเรียก API เพิ่มไปเช็ค user id เอง
    """
    text = message.text
    mention = message.mention
    if not mention or not mention.mentionees:
        return False, text

    self_mentions = [
        m for m in mention.mentionees
        if getattr(m, "type", None) == "user" and getattr(m, "is_self", False)
    ]
    if not self_mentions:
        return False, text

    for m in sorted(self_mentions, key=lambda m: m.index, reverse=True):
        text = text[:m.index] + text[m.index + m.length:]
    return True, text.strip()


def _match_trigger_keyword(text: str) -> tuple[bool, str]:
    """
    fallback สำหรับกลุ่ม/ห้องแชท เผื่อบัญชีไม่ขึ้นในลิสต์ @ ให้แท็ก (บัญชี LINE OA ที่ยังไม่ verified
    มักไม่ถูกดึงเข้าลิสต์ mention ในกลุ่ม ทำให้แท็กแบบ @ จริง ๆ ไม่ได้)
    ให้พิมพ์คำนำหน้าตามที่ตั้งไว้ใน GROUP_TRIGGER_KEYWORDS แทนได้ (ค่าเริ่มต้น: "บอท", "bot", "!")
    คืนค่า (ตรงคำนำหน้าไหม, ข้อความหลังตัดคำนำหน้าออก)
    """
    keywords = [k.strip() for k in os.getenv("GROUP_TRIGGER_KEYWORDS", "บอท,bot,!").split(",") if k.strip()]
    low = text.lower()
    for kw in keywords:
        if low.startswith(kw.lower()):
            return True, text[len(kw):].strip()
    return False, text


def _format_contact(c: dict) -> list[str]:
    role_label = "หลัก" if c.get("contact_role") == "PRIMARY" else "สำรอง"
    type_label = CONTACT_TYPE_LABEL.get(c.get("contact_type"), c.get("contact_type", ""))
    header = f"👤 {c['name']}"
    if c.get("position"):
        header += f" ({c['position']})"
    lines = [header]
    if c.get("organization_name"):
        lines.append(f"   🏢 {c['organization_name']}")
    lines.append(f"   🏷️ {type_label} · {role_label}" + (" · เปิด 24 ชม." if c.get("is_available_24h") else ""))
    if c.get("phone"):
        lines.append(f"   📞 {c['phone']}")
    if c.get("email"):
        lines.append(f"   ✉️ {c['email']}")
    if c.get("line_id"):
        lines.append(f"   💬 Line: {c['line_id']}")
    if c.get("note"):
        lines.append(f"   📝 {c['note']}")
    return lines


def _chunk_text(text: str, max_len: int = 4500, max_chunks: int = 5) -> list[str]:
    """ตัดข้อความยาว ๆ เป็นชิ้นละไม่เกิน max_len ตัวอักษร (ตัดที่ขึ้นบรรทัดใหม่ กันตัดกลางคำ)"""
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_len)
        if cut <= 0:
            cut = max_len
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if len(chunks) > max_chunks:
        chunks = chunks[:max_chunks]
        chunks[-1] += "\n\n⚠️ ข้อมูลมีเยอะเกินกว่าจะแสดงในแชทได้หมด (ตัดแสดงบางส่วน)"
    return chunks


def _parse_add_contact(text: str) -> tuple[dict | None, str | None]:
    """
    parse ข้อความหลายบรรทัดของคำสั่ง "เพิ่มติดต่อ"
    คืนค่า (fields, error_message) — ถ้า parse สำเร็จ error_message เป็น None
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or lines[0] != "เพิ่มติดต่อ":
        return None, None  # ไม่ใช่คำสั่งนี้

    labels = {
        "ชื่อ": "name", "หน่วยงาน": "organization", "ตำแหน่ง": "position",
        "ตัวย่อหน่วยงาน": "organization_code", "ตัวย่อ": "organization_code",
        "รหัสหน่วยงาน": "organization_code",
        "เบอร์": "phone", "โทร": "phone", "อีเมล": "email", "ไลน์": "line_id",
        "ประเภท": "contact_type", "บทบาท": "contact_role", "24ชม": "is_available_24h",
        "หมายเหตุ": "note",
    }
    raw: dict[str, str] = {}
    for ln in lines[1:]:
        if ":" not in ln:
            continue
        label, _, value = ln.partition(":")
        key = labels.get(label.strip())
        if key:
            raw[key] = value.strip()

    if not raw.get("name") or not raw.get("organization"):
        return None, "ขาดฟิลด์ที่จำเป็นครับ ต้องมีอย่างน้อย \"ชื่อ\" และ \"หน่วยงาน\""

    fields: dict = {"name": raw["name"], "organization": raw["organization"]}
    for k in ("phone", "email", "line_id", "position", "note"):
        if raw.get(k) and raw[k] != "-":
            fields[k] = raw[k]

    if raw.get("organization_code") and raw["organization_code"] != "-":
        code = raw["organization_code"].strip().upper()
        if len(code) > 30:
            return None, "ตัวย่อหน่วยงานยาวเกินไปครับ (สูงสุด 30 ตัวอักษร)"
        if any(ch.isspace() for ch in code):
            return None, "ตัวย่อหน่วยงานต้องไม่มีช่องว่างครับ เช่น IT, RFD, LAB"
        fields["organization_code"] = code

    if raw.get("contact_type"):
        v = raw["contact_type"].strip()
        mapped = CONTACT_TYPE_BY_LABEL.get(v, v.upper())
        if mapped not in CONTACT_TYPE_LABEL:
            return None, f"ประเภทไม่ถูกต้องครับ เลือกได้: {', '.join(CONTACT_TYPE_LABEL.values())}"
        fields["contact_type"] = mapped

    if raw.get("contact_role"):
        v = raw["contact_role"].strip()
        mapped = CONTACT_ROLE_BY_LABEL.get(v, v.upper())
        if mapped not in ("PRIMARY", "SECONDARY"):
            return None, "บทบาทไม่ถูกต้องครับ เลือกได้: หลัก, สำรอง"
        fields["contact_role"] = mapped

    if raw.get("is_available_24h"):
        fields["is_available_24h"] = raw["is_available_24h"].strip().lower() in TRUE_WORDS

    return fields, None


def _handle_legacy_command(chat_id: str, text: str, user_id: str | None) -> str | list[str]:
    t = text.strip()
    low = t.lower()

    if low in ("ช่วยเหลือ", "help", "เมนู", "คำสั่ง"):
        return HELP_TEXT

    if t == "ข่าว":
        items = news.fetch_headlines(query=None, limit=5)
        return news.format_plain("ข่าวเด่นวันนี้", items)

    if t.startswith("หา ") or t.startswith("ค้นหา "):
        query = t.split(" ", 1)[1].strip()
        items = news.fetch_headlines(query=query, limit=5)
        return news.format_plain(query, items)

    if t.startswith("หุ้น "):
        ticker = t.split(" ", 1)[1].strip().upper()
        return news.get_stock_price(ticker)

    if t.startswith("ติดต่อฉุกเฉิน"):
        contacts = db.list_emergency_contacts()
        if not contacts:
            return "ยังไม่มีข้อมูลผู้ติดต่อฉุกเฉินในระบบครับ"
        lines = [f"🚨 ผู้ติดต่อฉุกเฉิน ({len(contacts)} รายการ)"]
        for c in contacts:
            lines.extend(_format_contact(c))
        return "\n".join(lines)

    if t.startswith("ติดต่อ "):
        query = t.split(" ", 1)[1].strip()
        org_name, contacts, is_fuzzy = db.search_contacts(query)
        if not contacts:
            return f"ไม่พบข้อมูลติดต่อของ \"{query}\" ครับ"

        lines = []
        if is_fuzzy:
            guess = org_name if org_name else contacts[0]["name"]
            lines.append(f"ไม่พบ \"{query}\" ตรง ๆ ครับ เข้าใจว่าคุณหมายถึง \"{guess}\" ใช่ไหม 🤔")
        if org_name:
            lines.append(f"🏢 {org_name} — ผู้ติดต่อทั้งหมด ({len(contacts)} คน)")
        elif not is_fuzzy:
            lines.append(f"📇 พบ {len(contacts)} รายการสำหรับ \"{query}\"")
        for c in contacts:
            lines.extend(_format_contact(c))
        return "\n".join(lines)

    if t == "เพิ่มติดต่อ" or t.startswith("เพิ่มติดต่อ\n") or t.startswith("เพิ่มติดต่อ "):
        if not _is_admin(user_id):
            return "คำสั่งนี้ใช้ได้เฉพาะแอดมินครับ"
        fields, err = _parse_add_contact(t)
        if err:
            return f"⚠️ {err}\n\n{ADD_CONTACT_FORMAT_HELP}"
        if fields is None:
            return ADD_CONTACT_FORMAT_HELP
        contact_id = db.add_contact(fields)
        return f"✅ เพิ่ม \"{fields['name']}\" ({fields['organization']}) ลงฐานหลักแล้วครับ (ID: {contact_id})"

    if t == "ข้อมูลทั้งหมด":
        if not _is_admin(user_id):
            return "คำสั่งนี้ใช้ได้เฉพาะแอดมินครับ"
        contacts = db.dump_all()
        if not contacts:
            return "ฐานหลักยังไม่มีข้อมูลเลยครับ"

        body = [f"📦 ข้อมูลทั้งหมดในฐานหลัก ({len(contacts)} รายการ)"]
        last_org = None
        for c in contacts:
            org = c.get("organization_name") or "(ไม่มีหน่วยงาน)"
            if org != last_org:
                body.append(f"\n🏢 {org}")
                last_org = org
            body.extend(_format_contact(c))
        return _chunk_text("\n".join(body))

    if t == "ตรวจฐานข้อมูล":
        if not _is_admin(user_id):
            return "คำสั่งนี้ใช้ได้เฉพาะแอดมินครับ"
        status = db.database_status()
        lines = [
            "✅ เชื่อมต่อฐานข้อมูลหลักสำเร็จ",
            f"หน่วยงาน: {status['organization_count']} รายการ",
            f"ผู้ติดต่อ: {status['contact_count']} รายการ",
        ]
        return "\n".join(lines)

    if t.startswith("ติดตาม "):
        topic = t.split(" ", 1)[1].strip()
        added = storage.add_topic(chat_id, topic)
        storage.set_daily_subscription(chat_id, True)
        return (
            f"เพิ่ม \"{topic}\" เข้ารายการติดตามแล้ว จะรายงานให้ทุกวันครับ"
            if added else f"\"{topic}\" อยู่ในรายการติดตามอยู่แล้วครับ"
        )

    if t.startswith("เลิกติดตาม "):
        topic = t.split(" ", 1)[1].strip()
        removed = storage.remove_topic(chat_id, topic)
        return f"เอา \"{topic}\" ออกจากรายการติดตามแล้วครับ" if removed else f"ไม่พบ \"{topic}\" ในรายการติดตามครับ"

    if t == "รายการติดตาม":
        topics = storage.list_topics(chat_id)
        if not topics:
            return "ยังไม่มีหัวข้อที่ติดตามอยู่ครับ พิมพ์ \"ติดตาม <หัวข้อ>\" เพื่อเพิ่มได้เลย"
        return "📋 รายการที่ติดตามอยู่:\n" + "\n".join(f"• {tp}" for tp in topics)

    if t == "เปิดข่าวประจำวัน":
        storage.set_daily_subscription(chat_id, True)
        return "เปิดสรุปข่าวประจำวันแล้วครับ จะส่งให้ตามเวลาที่ตั้งไว้ทุกวัน"

    if t == "ปิดข่าวประจำวัน":
        storage.set_daily_subscription(chat_id, False)
        return "ปิดสรุปข่าวประจำวันแล้วครับ"

    # ไม่ตรงคำสั่งไหนเลย -> ใช้เป็นคำค้นข่าวทันที (โต้ตอบให้เป็นธรรมชาติ)
    items = news.fetch_headlines(query=t, limit=5)
    return news.format_plain(t, items)


def handle_command(chat_id: str, text: str, user_id: str | None, bot_id: str = "default") -> str | list[str]:
    """ทางเข้ากลาง: Service ใหม่ก่อน แล้วค่อย fallback ไปคำสั่งเดิมที่ยังไม่ได้ย้าย"""
    request = ServiceRequest(bot_id=bot_id, chat_id=chat_id, user_id=user_id, text=text)
    response = service_registry.dispatch(
        request,
        enabled_services(bot_id),
        fallback=lambda req: _handle_legacy_command(req.chat_id, req.text, req.user_id),
    )
    return response.message


@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if isinstance(event, JoinEvent):
            chat_id, chat_type = _get_chat_id(event)
            storage.register_chat(chat_id, chat_type)
            line_client.reply_text(
                event.reply_token,
                "สวัสดีครับ! ผมเป็นผู้ช่วยรายงานข่าวและค้นข้อมูล\n" + HELP_TEXT,
            )

        elif isinstance(event, LeaveEvent):
            chat_id, _ = _get_chat_id(event)
            storage.remove_chat(chat_id)

        elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            chat_id, chat_type = _get_chat_id(event)
            storage.register_chat(chat_id, chat_type)
            user_id = getattr(event.source, "user_id", None)

            text = event.message.text
            if chat_type in ("group", "room"):
                mentioned, text = _extract_self_mention(event.message)
                if not mentioned:
                    mentioned, text = _match_trigger_keyword(text)
                if not mentioned:
                    continue  # ไม่ถูกแท็ก/ไม่มีคำนำหน้าที่กำหนด -> เงียบไว้ ไม่ตอบ
                if not text:
                    text = "ช่วยเหลือ"  # เรียกเฉย ๆ ไม่มีคำสั่งต่อท้าย -> โชว์เมนูช่วยเหลือ

            try:
                reply = handle_command(chat_id, text, user_id)
            except Exception as e:
                print(f"[webhook] เกิดข้อผิดพลาดตอนประมวลผลข้อความ: {e}")
                reply = "ขออภัยครับ เกิดข้อผิดพลาดระหว่างประมวลผล ลองใหม่อีกครั้งนะครับ 🙏"

            if isinstance(reply, list):
                line_client.reply_texts(event.reply_token, reply)
            else:
                line_client.reply_text(event.reply_token, reply)

    return "OK"


@app.api_route("/", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "service": "line-news-bot"}


@app.on_event("startup")
async def on_startup():
    start_scheduler()

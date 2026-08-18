import os

from app.core.contracts import ServiceRequest, ServiceResponse


CONTACT_TYPE_LABEL = {
    "GENERAL": "ทั่วไป",
    "EMERGENCY": "ฉุกเฉิน",
    "MAINTENANCE": "ซ่อมบำรุง",
    "IT_SUPPORT": "IT",
    "LAB_SUPPORT": "แล็บ",
    "VENDOR": "ผู้ขาย/ผู้จำหน่าย",
    "OTHER": "อื่น ๆ",
}
CONTACT_TYPE_BY_LABEL = {label: value for value, label in CONTACT_TYPE_LABEL.items()}
CONTACT_ROLE_BY_LABEL = {"หลัก": "PRIMARY", "สำรอง": "SECONDARY"}
TRUE_WORDS = {"ใช่", "ได้", "yes", "true", "1"}

ADD_CONTACT_FORMAT_HELP = (
    "รูปแบบคำสั่งเพิ่มผู้ติดต่อ (พิมพ์หลายบรรทัดในข้อความเดียว):\n\n"
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
    "บังคับ: ชื่อ, หน่วยงาน (ตัวย่อไม่บังคับ)\n"
    f"ประเภท เลือกได้: {', '.join(CONTACT_TYPE_LABEL.values())}\n"
    "บทบาท เลือกได้: หลัก, สำรอง"
)


def _is_admin(user_id: str | None) -> bool:
    admin_ids = [
        value.strip()
        for value in os.getenv("LINE_ADMIN_USER_IDS", "").split(",")
        if value.strip()
    ]
    # รักษาพฤติกรรมเดิม: ถ้ายังไม่ตั้งค่า จะเปิดคำสั่งไว้เพื่อให้ตั้งระบบครั้งแรกได้
    return not admin_ids or user_id in admin_ids


def _parse_add_contact(text: str) -> tuple[dict | None, str | None]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "เพิ่มติดต่อ":
        return None, None

    labels = {
        "ชื่อ": "name",
        "หน่วยงาน": "organization",
        "ตัวย่อหน่วยงาน": "organization_code",
        "ตัวย่อ": "organization_code",
        "รหัสหน่วยงาน": "organization_code",
        "ตำแหน่ง": "position",
        "เบอร์": "phone",
        "โทร": "phone",
        "อีเมล": "email",
        "ไลน์": "line_id",
        "ประเภท": "contact_type",
        "บทบาท": "contact_role",
        "24ชม": "is_available_24h",
        "หมายเหตุ": "note",
    }
    raw: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        key = labels.get(label.strip())
        if key:
            raw[key] = value.strip()

    if not raw.get("name") or not raw.get("organization"):
        return None, 'ขาดฟิลด์ที่จำเป็นครับ ต้องมีอย่างน้อย "ชื่อ" และ "หน่วยงาน"'

    fields = {"name": raw["name"], "organization": raw["organization"]}
    for key in ("phone", "email", "line_id", "position", "note"):
        if raw.get(key) and raw[key] != "-":
            fields[key] = raw[key]

    if raw.get("organization_code") and raw["organization_code"] != "-":
        code = raw["organization_code"].strip().upper()
        if len(code) > 30:
            return None, "ตัวย่อหน่วยงานยาวเกินไปครับ (สูงสุด 30 ตัวอักษร)"
        if any(character.isspace() for character in code):
            return None, "ตัวย่อหน่วยงานต้องไม่มีช่องว่างครับ เช่น IT, RFD, LAB"
        fields["organization_code"] = code

    if raw.get("contact_type"):
        value = raw["contact_type"].strip()
        mapped = CONTACT_TYPE_BY_LABEL.get(value, value.upper())
        if mapped not in CONTACT_TYPE_LABEL:
            return None, f"ประเภทไม่ถูกต้องครับ เลือกได้: {', '.join(CONTACT_TYPE_LABEL.values())}"
        fields["contact_type"] = mapped

    if raw.get("contact_role"):
        value = raw["contact_role"].strip()
        mapped = CONTACT_ROLE_BY_LABEL.get(value, value.upper())
        if mapped not in ("PRIMARY", "SECONDARY"):
            return None, "บทบาทไม่ถูกต้องครับ เลือกได้: หลัก, สำรอง"
        fields["contact_role"] = mapped

    if raw.get("is_available_24h"):
        fields["is_available_24h"] = raw["is_available_24h"].strip().lower() in TRUE_WORDS
    return fields, None


def _format_contact(contact: dict) -> list[str]:
    role = "หลัก" if contact.get("contact_role") == "PRIMARY" else "สำรอง"
    contact_type = CONTACT_TYPE_LABEL.get(contact.get("contact_type"), contact.get("contact_type", ""))
    header = f"👤 {contact['name']}"
    if contact.get("position"):
        header += f" ({contact['position']})"
    lines = [header]
    lines.append(f"   🏷️ {contact_type} · {role}")
    if contact.get("phone"):
        lines.append(f"   📞 {contact['phone']}")
    if contact.get("email"):
        lines.append(f"   ✉️ {contact['email']}")
    return lines


def _chunk_text(text: str, max_len: int = 4500, max_chunks: int = 5) -> list[str]:
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_len)
        cut = cut if cut > 0 else max_len
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if len(chunks) > max_chunks:
        chunks = chunks[:max_chunks]
        chunks[-1] += "\n\n⚠️ ข้อมูลมีมากเกินกว่าจะแสดงได้หมด"
    return chunks


class AdminService:
    name = "admin"
    commands = ("เพิ่มติดต่อ", "ข้อมูลทั้งหมด", "ตรวจฐานข้อมูล")

    def __init__(self, repository=None, authorizer=None):
        if repository is None:
            from app import db as repository
        self.repository = repository
        self.authorizer = authorizer or _is_admin

    def can_handle(self, request: ServiceRequest) -> bool:
        text = request.text.strip()
        return (
            text == "เพิ่มติดต่อ"
            or text.startswith("เพิ่มติดต่อ\n")
            or text.startswith("เพิ่มติดต่อ ")
            or text == "ข้อมูลทั้งหมด"
            or text == "ตรวจฐานข้อมูล"
        )

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        if not self.authorizer(request.user_id):
            return ServiceResponse(False, self.name, "คำสั่งนี้ใช้ได้เฉพาะแอดมินครับ", error_code="FORBIDDEN")

        text = request.text.strip()
        if text.startswith("เพิ่มติดต่อ"):
            return self._add(text)
        if text == "ข้อมูลทั้งหมด":
            return self._dump_all()
        return self._database_status()

    def _add(self, text: str) -> ServiceResponse:
        fields, error = _parse_add_contact(text)
        if error:
            return ServiceResponse(False, self.name, f"⚠️ {error}\n\n{ADD_CONTACT_FORMAT_HELP}")
        if fields is None:
            return ServiceResponse(True, self.name, ADD_CONTACT_FORMAT_HELP)
        contact_id = self.repository.add_contact(fields)
        return ServiceResponse(
            True,
            self.name,
            f'✅ เพิ่ม "{fields["name"]}" ({fields["organization"]}) ลงฐานหลักแล้วครับ (ID: {contact_id})',
        )

    def _dump_all(self) -> ServiceResponse:
        contacts = self.repository.dump_all()
        if not contacts:
            return ServiceResponse(True, self.name, "ฐานหลักยังไม่มีข้อมูลเลยครับ")
        body = [f"📦 ข้อมูลทั้งหมดในฐานหลัก ({len(contacts)} รายการ)"]
        last_organization = None
        for contact in contacts:
            organization = contact.get("organization_name") or "(ไม่มีหน่วยงาน)"
            if organization != last_organization:
                body.append(f"\n🏢 {organization}")
                last_organization = organization
            body.extend(_format_contact(contact))
        return ServiceResponse(True, self.name, _chunk_text("\n".join(body)))

    def _database_status(self) -> ServiceResponse:
        status = self.repository.database_status()
        return ServiceResponse(
            True,
            self.name,
            "✅ เชื่อมต่อฐานข้อมูลหลักสำเร็จ\n"
            f"หน่วยงาน: {status['organization_count']} รายการ\n"
            f"ผู้ติดต่อ: {status['contact_count']} รายการ",
        )

    def health_check(self) -> bool:
        return True

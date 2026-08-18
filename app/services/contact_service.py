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


def _format_contact(contact: dict) -> list[str]:
    role = "หลัก" if contact.get("contact_role") == "PRIMARY" else "สำรอง"
    contact_type = CONTACT_TYPE_LABEL.get(
        contact.get("contact_type"), contact.get("contact_type", "")
    )
    header = f"👤 {contact['name']}"
    if contact.get("position"):
        header += f" ({contact['position']})"

    lines = [header]
    if contact.get("organization_name"):
        lines.append(f"   🏢 {contact['organization_name']}")
    availability = " · เปิด 24 ชม." if contact.get("is_available_24h") else ""
    lines.append(f"   🏷️ {contact_type} · {role}{availability}")
    if contact.get("phone"):
        lines.append(f"   📞 {contact['phone']}")
    if contact.get("email"):
        lines.append(f"   ✉️ {contact['email']}")
    if contact.get("line_id"):
        lines.append(f"   💬 Line: {contact['line_id']}")
    if contact.get("note"):
        lines.append(f"   📝 {contact['note']}")
    return lines


class ContactService:
    name = "contacts"
    commands = ("ติดต่อ", "ติดต่อฉุกเฉิน")

    def __init__(self, repository=None):
        if repository is None:
            from app import db as repository
        self.repository = repository

    def can_handle(self, request: ServiceRequest) -> bool:
        text = request.text.strip()
        return text == "ติดต่อฉุกเฉิน" or text.startswith("ติดต่อ ")

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        text = request.text.strip()
        if text == "ติดต่อฉุกเฉิน":
            return self._emergency_contacts()
        query = text.split(" ", 1)[1].strip()
        if not query:
            return ServiceResponse(False, self.name, "กรุณาระบุชื่อ เบอร์ อีเมล หรือหน่วยงานครับ")
        return self._search(query)

    def _emergency_contacts(self) -> ServiceResponse:
        contacts = self.repository.list_emergency_contacts()
        if not contacts:
            return ServiceResponse(True, self.name, "ยังไม่มีข้อมูลผู้ติดต่อฉุกเฉินในระบบครับ")
        lines = [f"🚨 ผู้ติดต่อฉุกเฉิน ({len(contacts)} รายการ)"]
        for contact in contacts:
            lines.extend(_format_contact(contact))
        return ServiceResponse(True, self.name, "\n".join(lines))

    def _search(self, query: str) -> ServiceResponse:
        organization, contacts, is_fuzzy = self.repository.search_contacts(query)
        if not contacts:
            return ServiceResponse(True, self.name, f"ไม่พบข้อมูลติดต่อของ \"{query}\" ครับ")

        lines: list[str] = []
        if is_fuzzy:
            guess = organization or contacts[0]["name"]
            lines.append(f"ไม่พบ \"{query}\" ตรง ๆ ครับ เข้าใจว่าคุณหมายถึง \"{guess}\" ใช่ไหม 🤔")
        if organization:
            lines.append(f"🏢 {organization} — ผู้ติดต่อทั้งหมด ({len(contacts)} คน)")
        elif not is_fuzzy:
            lines.append(f"📇 พบ {len(contacts)} รายการสำหรับ \"{query}\"")
        for contact in contacts:
            lines.extend(_format_contact(contact))
        return ServiceResponse(True, self.name, "\n".join(lines))

    def health_check(self) -> bool:
        # ไม่ยิง query ทุกครั้งเพื่อหลีกเลี่ยงโหลดฐานข้อมูล; health endpoint เฉพาะจะเพิ่มภายหลัง
        return True

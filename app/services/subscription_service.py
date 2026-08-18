from app.core.contracts import ServiceRequest, ServiceResponse


class SubscriptionService:
    name = "subscriptions"
    commands = (
        "ติดตาม",
        "เลิกติดตาม",
        "รายการติดตาม",
        "เปิดข่าวประจำวัน",
        "ปิดข่าวประจำวัน",
    )

    def __init__(self, repository=None):
        if repository is None:
            from app import storage as repository
        self.repository = repository

    def can_handle(self, request: ServiceRequest) -> bool:
        text = request.text.strip()
        return (
            text == "รายการติดตาม"
            or text == "เปิดข่าวประจำวัน"
            or text == "ปิดข่าวประจำวัน"
            or text == "ติดตาม"
            or text.startswith("ติดตาม ")
            or text == "เลิกติดตาม"
            or text.startswith("เลิกติดตาม ")
        )

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        text = request.text.strip()
        if text == "รายการติดตาม":
            return self._list(request.chat_id)
        if text == "เปิดข่าวประจำวัน":
            self.repository.set_daily_subscription(request.chat_id, True)
            return ServiceResponse(
                True,
                self.name,
                "เปิดสรุปข่าวประจำวันแล้วครับ จะส่งให้ตามเวลาที่ตั้งไว้ทุกวัน",
            )
        if text == "ปิดข่าวประจำวัน":
            self.repository.set_daily_subscription(request.chat_id, False)
            return ServiceResponse(True, self.name, "ปิดสรุปข่าวประจำวันแล้วครับ")
        if text == "ติดตาม":
            return ServiceResponse(False, self.name, "กรุณาระบุหัวข้อ เช่น ติดตาม ราคาน้ำมัน")
        if text == "เลิกติดตาม":
            return ServiceResponse(False, self.name, "กรุณาระบุหัวข้อ เช่น เลิกติดตาม ราคาน้ำมัน")
        if text.startswith("ติดตาม "):
            return self._add(request.chat_id, text.split(" ", 1)[1].strip())
        return self._remove(request.chat_id, text.split(" ", 1)[1].strip())

    def _add(self, chat_id: str, topic: str) -> ServiceResponse:
        if not topic:
            return ServiceResponse(False, self.name, "กรุณาระบุหัวข้อที่ต้องการติดตามครับ")
        added = self.repository.add_topic(chat_id, topic)
        self.repository.set_daily_subscription(chat_id, True)
        message = (
            f'เพิ่ม "{topic}" เข้ารายการติดตามแล้ว จะรายงานให้ทุกวันครับ'
            if added
            else f'"{topic}" อยู่ในรายการติดตามอยู่แล้วครับ'
        )
        return ServiceResponse(True, self.name, message)

    def _remove(self, chat_id: str, topic: str) -> ServiceResponse:
        if not topic:
            return ServiceResponse(False, self.name, "กรุณาระบุหัวข้อที่ต้องการเลิกติดตามครับ")
        removed = self.repository.remove_topic(chat_id, topic)
        message = (
            f'เอา "{topic}" ออกจากรายการติดตามแล้วครับ'
            if removed
            else f'ไม่พบ "{topic}" ในรายการติดตามครับ'
        )
        return ServiceResponse(True, self.name, message)

    def _list(self, chat_id: str) -> ServiceResponse:
        topics = self.repository.list_topics(chat_id)
        if not topics:
            return ServiceResponse(
                True,
                self.name,
                'ยังไม่มีหัวข้อที่ติดตามอยู่ครับ พิมพ์ "ติดตาม <หัวข้อ>" เพื่อเพิ่มได้เลย',
            )
        return ServiceResponse(
            True,
            self.name,
            "📋 รายการที่ติดตามอยู่:\n" + "\n".join(f"• {topic}" for topic in topics),
        )

    def health_check(self) -> bool:
        return True

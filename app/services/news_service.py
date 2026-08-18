from app import news
from app.core.contracts import ServiceRequest, ServiceResponse


class NewsService:
    name = "news"
    commands = ("ข่าว", "หา", "ค้นหา")

    def can_handle(self, request: ServiceRequest) -> bool:
        text = request.text.strip()
        return text == "ข่าว" or text.startswith("หา ") or text.startswith("ค้นหา ")

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        text = request.text.strip()
        query = None if text == "ข่าว" else text.split(" ", 1)[1].strip()
        label = query or "ข่าวเด่นวันนี้"
        items = news.fetch_headlines(query=query, limit=5)
        # ข่าวไม่บังคับพึ่ง AI: จัดรูปแบบ plain เสมอ
        return ServiceResponse(True, self.name, news.format_plain(label, items))

    def health_check(self) -> bool:
        return True

import os

from app.core.contracts import ServiceRequest, ServiceResponse


VALID_MODES = ("none", "local", "gemini", "anthropic")


class SettingsService:
    name = "settings"
    commands = ("โหมด",)

    def __init__(self, repository=None, environ=None):
        if repository is None:
            from app import storage as repository
        self.repository = repository
        self.environ = os.environ if environ is None else environ

    def can_handle(self, request: ServiceRequest) -> bool:
        text = request.text.strip()
        return text == "โหมด" or text.startswith("โหมด ")

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        text = request.text.strip()
        current = (
            self.repository.get_setting("ai_provider")
            or self.environ.get("AI_PROVIDER", "gemini")
        )
        parts = text.split(maxsplit=1)

        if len(parts) == 1:
            return ServiceResponse(
                True,
                self.name,
                f'โหมด AI ถามตอบตอนนี้: "{current}"\n'
                "เปลี่ยนได้ด้วย: โหมด none / โหมด local / โหมด gemini / โหมด anthropic",
            )

        mode = parts[1].strip().lower()
        if mode not in VALID_MODES:
            return ServiceResponse(
                False,
                self.name,
                f"โหมดไม่ถูกต้องครับ เลือกได้แค่: {', '.join(VALID_MODES)}",
                error_code="INVALID_MODE",
            )

        self.repository.set_setting("ai_provider", mode)
        return ServiceResponse(
            True,
            self.name,
            f'เปลี่ยนโหมด AI ถามตอบจาก "{current}" เป็น "{mode}" แล้วครับ',
        )

    def health_check(self) -> bool:
        return True

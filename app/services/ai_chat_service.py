from app import ai_chat
from app.core.contracts import ServiceRequest, ServiceResponse


class AIChatService:
    name = "ai_chat"
    commands = ("ถาม", "ai")

    def can_handle(self, request: ServiceRequest) -> bool:
        text = request.text.strip().lower()
        return text in ("ถาม", "ai") or text.startswith("ถาม ") or text.startswith("ai ")

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        parts = request.text.strip().split(maxsplit=1)
        if len(parts) == 1 or not parts[1].strip():
            return ServiceResponse(
                False,
                self.name,
                'กรุณาพิมพ์คำถาม เช่น "ถาม Python คืออะไร"',
                error_code="MISSING_QUESTION",
            )
        question = parts[1].strip()
        if ai_chat.get_provider() == "none":
            return ServiceResponse(
                False,
                self.name,
                'AI ถามตอบถูกปิดอยู่ครับ ใช้คำสั่ง "โหมด gemini" เพื่อเปิด',
                error_code="AI_DISABLED",
            )
        result = ai_chat.ask(question, conversation_id=request.chat_id)
        return ServiceResponse(
            True,
            self.name,
            result["answer"],
            metadata={"provider": result["provider"], "model": result["model"]},
        )

    def health_check(self) -> bool:
        return ai_chat.is_configured()

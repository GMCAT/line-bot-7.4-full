import unittest
from unittest.mock import patch

from app.core.contracts import ServiceRequest
from app.services.ai_chat_service import AIChatService


def request(text):
    return ServiceRequest("default", "chat-1", "user-1", text)


class AIChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AIChatService()

    def test_recognizes_bare_and_full_question_commands(self):
        self.assertTrue(self.service.can_handle(request("ถาม")))
        self.assertTrue(self.service.can_handle(request("ถาม Python คืออะไร")))
        self.assertTrue(self.service.can_handle(request("ai hello")))
        self.assertFalse(self.service.can_handle(request("ข่าว AI")))

    def test_bare_command_returns_usage_instead_of_news_fallback(self):
        response = self.service.handle(request("ถาม"))
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "MISSING_QUESTION")
        self.assertIn("กรุณาพิมพ์คำถาม", response.message)

    @patch("app.services.ai_chat_service.ai_chat.get_provider", return_value="none")
    def test_none_mode_disables_only_ai_chat(self, _provider):
        response = self.service.handle(request("ถาม สวัสดี"))
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "AI_DISABLED")

    @patch("app.services.ai_chat_service.ai_chat.ask")
    @patch("app.services.ai_chat_service.ai_chat.get_provider", return_value="gemini")
    def test_question_uses_selected_ai_provider(self, _provider, ask):
        ask.return_value = {
            "answer": "คำตอบทดสอบ",
            "provider": "gemini",
            "model": "gemini-3.6-flash",
        }
        response = self.service.handle(request("ถาม ทดสอบ"))
        self.assertTrue(response.success)
        self.assertEqual(response.message, "คำตอบทดสอบ")
        self.assertEqual(response.metadata["provider"], "gemini")
        ask.assert_called_once_with("ทดสอบ", conversation_id="chat-1")


if __name__ == "__main__":
    unittest.main()

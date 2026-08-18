import unittest

from app.core.contracts import ServiceRequest
from app.services.settings_service import SettingsService


class FakeRepository:
    def __init__(self, value=None):
        self.value = value
        self.writes = []

    def get_setting(self, key):
        return self.value

    def set_setting(self, key, value):
        self.value = value
        self.writes.append((key, value))


def request(text):
    return ServiceRequest("default", "chat-1", "user-1", text)


class SettingsServiceTests(unittest.TestCase):
    def test_recognizes_only_mode_commands(self):
        service = SettingsService(FakeRepository(), {})
        self.assertTrue(service.can_handle(request("โหมด")))
        self.assertTrue(service.can_handle(request("โหมด gemini")))
        self.assertFalse(service.can_handle(request("ถาม โหมดอะไร")))

    def test_reads_environment_default(self):
        service = SettingsService(FakeRepository(), {"AI_PROVIDER": "local"})
        response = service.handle(request("โหมด"))
        self.assertTrue(response.success)
        self.assertIn('"local"', response.message)

    def test_saved_setting_overrides_environment(self):
        service = SettingsService(FakeRepository("gemini"), {"AI_PROVIDER": "local"})
        response = service.handle(request("โหมด"))
        self.assertIn('"gemini"', response.message)

    def test_changes_valid_mode(self):
        repository = FakeRepository("none")
        service = SettingsService(repository, {})
        response = service.handle(request("โหมด ANTHROPIC"))
        self.assertTrue(response.success)
        self.assertEqual(repository.writes, [("ai_provider", "anthropic")])
        self.assertIn('"none" เป็น "anthropic"', response.message)

    def test_rejects_invalid_mode_without_writing(self):
        repository = FakeRepository("none")
        service = SettingsService(repository, {})
        response = service.handle(request("โหมด openai"))
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "INVALID_MODE")
        self.assertEqual(repository.writes, [])


if __name__ == "__main__":
    unittest.main()

import unittest

from app.core.contracts import ServiceRequest
from app.services.subscription_service import SubscriptionService


class FakeRepository:
    def __init__(self):
        self.topics = {}
        self.daily = {}

    def add_topic(self, chat_id, topic):
        values = self.topics.setdefault(chat_id, [])
        if topic in values:
            return False
        values.append(topic)
        return True

    def remove_topic(self, chat_id, topic):
        values = self.topics.get(chat_id, [])
        if topic not in values:
            return False
        values.remove(topic)
        return True

    def list_topics(self, chat_id):
        return self.topics.get(chat_id, [])

    def set_daily_subscription(self, chat_id, enabled):
        self.daily[chat_id] = enabled


def request(text, chat_id="chat-1"):
    return ServiceRequest("default", chat_id, "user", text)


class SubscriptionServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.service = SubscriptionService(self.repository)

    def test_recognizes_subscription_commands(self):
        self.assertTrue(self.service.can_handle(request("ติดตาม ราคาน้ำมัน")))
        self.assertTrue(self.service.can_handle(request("รายการติดตาม")))
        self.assertFalse(self.service.can_handle(request("ติดต่อ สมชาย")))

    def test_add_enables_daily_and_prevents_duplicate(self):
        first = self.service.handle(request("ติดตาม ราคาน้ำมัน"))
        second = self.service.handle(request("ติดตาม ราคาน้ำมัน"))
        self.assertIn("เพิ่ม", first.message)
        self.assertIn("อยู่ในรายการ", second.message)
        self.assertTrue(self.repository.daily["chat-1"])

    def test_list_and_remove(self):
        self.service.handle(request("ติดตาม AAPL"))
        listed = self.service.handle(request("รายการติดตาม"))
        self.assertIn("AAPL", listed.message)
        removed = self.service.handle(request("เลิกติดตาม AAPL"))
        self.assertIn("ออกจากรายการ", removed.message)

    def test_daily_toggle(self):
        self.service.handle(request("เปิดข่าวประจำวัน"))
        self.assertTrue(self.repository.daily["chat-1"])
        self.service.handle(request("ปิดข่าวประจำวัน"))
        self.assertFalse(self.repository.daily["chat-1"])

    def test_missing_topic_returns_help(self):
        response = self.service.handle(request("ติดตาม"))
        self.assertFalse(response.success)
        self.assertIn("กรุณาระบุหัวข้อ", response.message)


if __name__ == "__main__":
    unittest.main()

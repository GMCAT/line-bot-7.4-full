import unittest
from app.core.contracts import ServiceRequest
from app.services.contact_service import ContactService


def request(text):
    return ServiceRequest("default", "chat", "user", text)


CONTACT = {
    "name": "นายเอ",
    "organization_name": "กรมทดสอบ",
    "position": "หัวหน้าฝ่าย",
    "contact_role": "PRIMARY",
    "contact_type": "EMERGENCY",
    "is_available_24h": True,
    "phone": "0812345678",
    "email": "a@example.com",
    "line_id": None,
    "note": None,
}


class ContactServiceTests(unittest.TestCase):
    def setUp(self):
        class FakeRepository:
            search_result = (None, [], False)
            emergency_result = []

            def search_contacts(self, query):
                return self.search_result

            def list_emergency_contacts(self):
                return self.emergency_result

        self.repository = FakeRepository()
        self.service = ContactService(repository=self.repository)

    def test_recognizes_only_contact_commands(self):
        self.assertTrue(self.service.can_handle(request("ติดต่อ นายเอ")))
        self.assertTrue(self.service.can_handle(request("ติดต่อฉุกเฉิน")))
        self.assertFalse(self.service.can_handle(request("เพิ่มติดต่อ")))

    def test_search_contact(self):
        self.repository.search_result = ("กรมทดสอบ", [CONTACT], False)
        response = self.service.handle(request("ติดต่อ กรมทดสอบ"))
        self.assertTrue(response.success)
        self.assertIn("นายเอ", response.message)
        self.assertIn("0812345678", response.message)

    def test_empty_search_result(self):
        self.repository.search_result = (None, [], False)
        response = self.service.handle(request("ติดต่อ ไม่มีคนนี้"))
        self.assertIn("ไม่พบข้อมูลติดต่อ", response.message)

    def test_emergency_contacts(self):
        self.repository.emergency_result = [CONTACT]
        response = self.service.handle(request("ติดต่อฉุกเฉิน"))
        self.assertIn("ผู้ติดต่อฉุกเฉิน", response.message)
        self.assertIn("เปิด 24 ชม.", response.message)


if __name__ == "__main__":
    unittest.main()

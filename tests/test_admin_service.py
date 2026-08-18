import unittest

from app.core.contracts import ServiceRequest
from app.services.admin_service import AdminService, _parse_add_contact


class FakeRepository:
    def __init__(self):
        self.last_fields = None

    def add_contact(self, fields):
        self.last_fields = fields
        return 42

    def dump_all(self):
        return []

    def database_status(self):
        return {"organization_count": 2, "contact_count": 5}


def request(text, user_id="admin"):
    return ServiceRequest("default", "chat", user_id, text)


class AdminServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.service = AdminService(self.repository, authorizer=lambda user_id: user_id == "admin")

    def test_recognizes_admin_commands_only(self):
        self.assertTrue(self.service.can_handle(request("ตรวจฐานข้อมูล")))
        self.assertTrue(self.service.can_handle(request("เพิ่มติดต่อ\nชื่อ: นายเอ")))
        self.assertFalse(self.service.can_handle(request("ติดต่อ นายเอ")))

    def test_rejects_non_admin(self):
        response = self.service.handle(request("ตรวจฐานข้อมูล", "user"))
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "FORBIDDEN")

    def test_add_contact_with_organization_code(self):
        response = self.service.handle(request(
            "เพิ่มติดต่อ\nชื่อ: นายเอ\nหน่วยงาน: ฝ่ายไอที\nตัวย่อหน่วยงาน: it\nประเภท: IT\nบทบาท: หลัก"
        ))
        self.assertTrue(response.success)
        self.assertEqual(self.repository.last_fields["organization_code"], "IT")
        self.assertEqual(self.repository.last_fields["contact_type"], "IT_SUPPORT")
        self.assertIn("ID: 42", response.message)

    def test_missing_required_fields_returns_form_help(self):
        response = self.service.handle(request("เพิ่มติดต่อ\nชื่อ: นายเอ"))
        self.assertFalse(response.success)
        self.assertIn("ขาดฟิลด์", response.message)

    def test_database_status(self):
        response = self.service.handle(request("ตรวจฐานข้อมูล"))
        self.assertIn("หน่วยงาน: 2", response.message)
        self.assertIn("ผู้ติดต่อ: 5", response.message)

    def test_parser_rejects_code_with_spaces(self):
        fields, error = _parse_add_contact(
            "เพิ่มติดต่อ\nชื่อ: นายเอ\nหน่วยงาน: ฝ่ายไอที\nตัวย่อหน่วยงาน: I T"
        )
        self.assertIsNone(fields)
        self.assertIn("ไม่มีช่องว่าง", error)


if __name__ == "__main__":
    unittest.main()

import unittest

from app.core.contracts import ServiceRequest, ServiceResponse
from app.core.registry import ServiceRegistry


class EchoService:
    name = "echo"
    commands = ("echo",)

    def can_handle(self, request):
        return request.text.startswith("echo ")

    def handle(self, request):
        return ServiceResponse(True, self.name, request.text[5:])

    def health_check(self):
        return True


class BrokenService(EchoService):
    name = "broken"

    def can_handle(self, request):
        return request.text == "break"

    def handle(self, request):
        raise RuntimeError("boom")


def request(text):
    return ServiceRequest("default", "chat", "user", text)


class RegistryTests(unittest.TestCase):
    def test_dispatches_enabled_service(self):
        registry = ServiceRegistry()
        registry.register(EchoService())
        response = registry.dispatch(request("echo hello"), {"echo"}, lambda _: "fallback")
        self.assertEqual(response.service, "echo")
        self.assertEqual(response.message, "hello")

    def test_disabled_service_does_not_reach_legacy_fallback(self):
        registry = ServiceRegistry()
        registry.register(EchoService())
        response = registry.dispatch(request("echo hello"), set(), lambda _: "fallback")
        self.assertEqual(response.service, "echo")
        self.assertEqual(response.error_code, "SERVICE_DISABLED")

    def test_failure_is_isolated(self):
        registry = ServiceRegistry()
        registry.register(BrokenService())
        response = registry.dispatch(request("break"), {"broken"}, lambda _: "fallback")
        self.assertFalse(response.success)
        self.assertEqual(response.service, "broken")
        self.assertTrue(response.retryable)


if __name__ == "__main__":
    unittest.main()

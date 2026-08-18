from app.core.registry import ServiceRegistry


def build_registry() -> ServiceRegistry:
    # import แบบ lazy เพื่อให้ Service ที่ dependency เสีย ไม่ทำให้ import package ทั้งชุดล้ม
    from app.services.ai_chat_service import AIChatService
    from app.services.admin_service import AdminService
    from app.services.contact_service import ContactService
    from app.services.news_service import NewsService
    from app.services.settings_service import SettingsService
    from app.services.stock_service import StockService
    from app.services.subscription_service import SubscriptionService

    registry = ServiceRegistry()
    registry.register(NewsService())
    registry.register(StockService())
    registry.register(AIChatService())
    registry.register(ContactService())
    registry.register(SubscriptionService())
    registry.register(AdminService())
    registry.register(SettingsService())
    return registry

from app import news
from app.core.contracts import ServiceRequest, ServiceResponse


class StockService:
    name = "stocks"
    commands = ("หุ้น",)

    def can_handle(self, request: ServiceRequest) -> bool:
        return request.text.strip().startswith("หุ้น ")

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        ticker = request.text.strip().split(" ", 1)[1].strip().upper()
        return ServiceResponse(True, self.name, news.get_stock_price(ticker))

    def health_check(self) -> bool:
        return True

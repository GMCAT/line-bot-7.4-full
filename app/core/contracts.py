from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ServiceRequest:
    bot_id: str
    chat_id: str
    user_id: str | None
    text: str
    command: str = ""
    argument: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceResponse:
    success: bool
    service: str
    message: str | list[str]
    retryable: bool = False
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BotService(Protocol):
    name: str
    commands: tuple[str, ...]

    def can_handle(self, request: ServiceRequest) -> bool: ...

    def handle(self, request: ServiceRequest) -> ServiceResponse: ...

    def health_check(self) -> bool: ...

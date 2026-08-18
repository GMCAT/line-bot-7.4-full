import os
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)

_configuration = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])


def reply_text(reply_token: str, text: str) -> None:
    with ApiClient(_configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text[:4900])],  # LINE limit ~5000 ตัวอักษร
            )
        )


def reply_texts(reply_token: str, texts: list[str]) -> None:
    """ตอบหลายข้อความพร้อมกันในครั้งเดียว — LINE reply API รับได้สูงสุด 5 ข้อความต่อ reply_token"""
    with ApiClient(_configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=t[:4900]) for t in texts[:5]],
            )
        )


def push_text(chat_id: str, text: str) -> None:
    with ApiClient(_configuration) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(
                to=chat_id,
                messages=[TextMessage(text=text[:4900])],
            )
        )

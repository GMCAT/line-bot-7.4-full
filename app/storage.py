"""
เก็บข้อมูลแบบง่าย ๆ ด้วยไฟล์ JSON — พอสำหรับบอทขนาดส่วนตัว/ทีมเล็ก
โครงสร้างข้อมูล:
{
  "chats": {
    "<chat_id>": {
      "type": "group" | "user",
      "subscribed_daily": true,
      "topics": ["ราคาหุ้น AAPL", "ข่าวเทคโนโลยี"]
    }
  },
  "settings": {
    "ai_provider": "gemini"   # override ค่า AI_PROVIDER จาก env ตอนรันไทม์ (ตั้งผ่านคำสั่ง "โหมด")
  }
}
"""
import json
import os
import threading
from pathlib import Path

_lock = threading.Lock()


def _storage_path() -> Path:
    path = Path(os.getenv("STORAGE_FILE", "data/storage.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load() -> dict:
    path = _storage_path()
    if not path.exists():
        return {"chats": {}, "settings": {}}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        data.setdefault("chats", {})
        data.setdefault("settings", {})
        return data


def _save(data: dict) -> None:
    path = _storage_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_chat(chat_id: str, chat_type: str) -> None:
    with _lock:
        data = _load()
        if chat_id not in data["chats"]:
            data["chats"][chat_id] = {
                "type": chat_type,
                "subscribed_daily": False,
                "topics": [],
            }
            _save(data)


def set_daily_subscription(chat_id: str, enabled: bool) -> None:
    with _lock:
        data = _load()
        data["chats"].setdefault(chat_id, {"type": "user", "subscribed_daily": False, "topics": []})
        data["chats"][chat_id]["subscribed_daily"] = enabled
        _save(data)


def add_topic(chat_id: str, topic: str) -> bool:
    with _lock:
        data = _load()
        chat = data["chats"].setdefault(chat_id, {"type": "user", "subscribed_daily": False, "topics": []})
        if topic in chat["topics"]:
            return False
        chat["topics"].append(topic)
        _save(data)
        return True


def remove_topic(chat_id: str, topic: str) -> bool:
    with _lock:
        data = _load()
        chat = data["chats"].get(chat_id)
        if not chat or topic not in chat["topics"]:
            return False
        chat["topics"].remove(topic)
        _save(data)
        return True


def list_topics(chat_id: str) -> list[str]:
    data = _load()
    return data["chats"].get(chat_id, {}).get("topics", [])


def all_chats() -> dict:
    return _load()["chats"]


def remove_chat(chat_id: str) -> None:
    with _lock:
        data = _load()
        data["chats"].pop(chat_id, None)
        _save(data)


def get_setting(key: str, default=None):
    return _load()["settings"].get(key, default)


def set_setting(key: str, value) -> None:
    with _lock:
        data = _load()
        data["settings"][key] = value
        _save(data)

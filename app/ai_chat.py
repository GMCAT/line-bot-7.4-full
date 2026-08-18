"""AI สำหรับถามตอบทั่วไป แยกจากระบบข่าวโดยสมบูรณ์"""
import logging
import os


SYSTEM_PROMPT = os.getenv(
    "AI_SYSTEM_PROMPT",
    "คุณเป็นผู้ช่วยภาษาไทย ตอบให้ถูกต้อง กระชับ และบอกอย่างตรงไปตรงมาหากไม่แน่ใจ",
)
logger = logging.getLogger(__name__)


def get_provider() -> str:
    """อ่านค่าที่สั่งผ่าน LINE ก่อน แล้วค่อย fallback ไป AI_PROVIDER ของ Render"""
    from app import storage

    return (storage.get_setting("ai_provider") or os.getenv("AI_PROVIDER", "gemini")).lower()


def is_configured() -> bool:
    provider = get_provider()
    required = {
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "local": "LOCAL_AI_BASE_URL",
    }
    return provider != "none" and bool(os.getenv(required.get(provider, ""), ""))


def _ask_gemini(question: str) -> dict:
    import httpx

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError("ยังไม่ได้ตั้ง GEMINI_API_KEY ที่ใช้งานได้")

    configured_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
    models = list(dict.fromkeys([configured_model, "gemini-3.6-flash", "gemini-3.5-flash"]))
    errors = []
    for model in models:
        try:
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": api_key},
                json={"contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nคำถาม: {question}"}]}]},
                timeout=30,
            )
            if response.is_error:
                try:
                    detail = response.json().get("error", {}).get("message", response.text)
                except ValueError:
                    detail = response.text
                errors.append(f"{model}: HTTP {response.status_code} {' '.join(detail.split())[:300]}")
                continue
            answer = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if not answer:
                raise ValueError("Gemini ส่งข้อความว่างกลับมา")
            return {"answer": answer, "provider": "gemini", "model": model}
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            errors.append(f"{model}: {type(exc).__name__} {exc}")

    logger.error("Gemini ถามตอบล้มเหลว: %s", " | ".join(errors))
    raise RuntimeError("เรียก Gemini ไม่สำเร็จ กรุณาตรวจ GEMINI_API_KEY, GEMINI_MODEL และ Render Logs")


def _ask_local(question: str) -> dict:
    import httpx

    base_url = os.environ["LOCAL_AI_BASE_URL"].rstrip("/")
    model = os.getenv("LOCAL_AI_MODEL", "gemma-4-31b-it")
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LOCAL_AI_API_KEY', 'ollama')}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "stream": False,
        },
        timeout=45,
    )
    response.raise_for_status()
    answer = response.json()["choices"][0]["message"]["content"].strip()
    return {"answer": answer, "provider": "local", "model": model}


def _ask_anthropic(question: str) -> dict:
    from anthropic import Anthropic

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    response = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(
        model=model,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    answer = "".join(block.text for block in response.content if block.type == "text")
    return {"answer": answer, "provider": "anthropic", "model": model}


def ask(question: str, conversation_id: str | None = None) -> dict:
    del conversation_id  # เตรียม interface ไว้สำหรับเพิ่ม memory ในระยะถัดไป
    if not question:
        raise ValueError("คำถามต้องไม่ว่าง")
    provider = get_provider()
    if provider == "none":
        raise RuntimeError('AI ถามตอบถูกปิดอยู่ครับ ใช้คำสั่ง "โหมด gemini" เพื่อเปิด')
    handlers = {"gemini": _ask_gemini, "local": _ask_local, "anthropic": _ask_anthropic}
    if provider not in handlers:
        raise ValueError("AI_PROVIDER ต้องเป็น gemini, local หรือ anthropic")
    return handlers[provider](question)

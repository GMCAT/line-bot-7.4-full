import unittest

from app import news


class NewsPlainOnlyTests(unittest.TestCase):
    def test_news_module_has_no_ai_summarizers(self):
        self.assertFalse(hasattr(news, "_summarize_with_gemini"))
        self.assertFalse(hasattr(news, "_summarize_with_local"))
        self.assertFalse(hasattr(news, "_summarize_with_anthropic"))

    def test_news_output_is_plain_and_keeps_source_link(self):
        items = [{
            "title": "ข่าวทดสอบ",
            "link": "https://example.com/news",
            "published": "",
            "source": "สำนักข่าวทดสอบ",
        }]
        result = news.format_plain("ข่าวเด่นวันนี้", items)
        self.assertIn("ข่าวทดสอบ", result)
        self.assertIn("https://example.com/news", result)

if __name__ == "__main__":
    unittest.main()

import unittest
from src.engine.email_dispatcher import EmailDispatcher
from src.engine.rate_limiter import RateLimiter

class TestEmailDispatcher(unittest.TestCase):
    def test_email_message_construction(self):
        dispatcher = EmailDispatcher()
        msg = dispatcher.build_message(
            recipient_email="curator@blog.com",
            subject="Pitch: Midnight Reverie",
            text_body="Hello curator,\n\nCheck out my new track.",
            html_body="<p>Hello curator,</p><p>Check out my new track.</p>",
            in_reply_to="<orig-123@kxrn.music>",
            references="<orig-123@kxrn.music>"
        )

        self.assertEqual(msg["To"], "curator@blog.com")
        self.assertEqual(msg["Subject"], "Pitch: Midnight Reverie")
        self.assertEqual(msg["In-Reply-To"], "<orig-123@kxrn.music>")
        self.assertEqual(msg["References"], "<orig-123@kxrn.music>")
        self.assertTrue(msg["Message-ID"].endswith("@kxrn.music>"))

        # Check multipart structure
        payloads = msg.get_payload()
        self.assertEqual(len(payloads), 2)
        self.assertEqual(payloads[0].get_content_type(), "text/plain")
        self.assertEqual(payloads[1].get_content_type(), "text/html")

    def test_rate_limiter_stats(self):
        count_before = RateLimiter.get_today_sent_count()
        self.assertGreaterEqual(count_before, 0)
        self.assertIsInstance(RateLimiter.can_send(), bool)

if __name__ == "__main__":
    unittest.main()

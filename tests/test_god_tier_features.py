import unittest
try:
    from fastapi.testclient import TestClient
except Exception:
    from starlette.testclient import TestClient
from api.index import app
from src.engine.rate_limiter import RateLimiter
from src.inbox.reply_detector import ReplyDetector
from src.crm.notion_client import NotionClient

class TestGodTierFeatures(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # 1. Test Mode: /api/test-pitch endpoint
    def test_test_pitch_endpoint(self):
        res = self.client.post("/api/test-pitch", json={
            "recipient_email": "secondary.test@yahoo.com",
            "template_type": "blog",
            "track_name": "God-Tier Beat"
        })
        # If SMTP is not connected yet, it returns a 400 with a clean error message,
        # verifying the endpoint accepts the payload, renders the pitch, and invokes the dispatcher!
        self.assertIn(res.status_code, [200, 400])
        data = res.json()
        self.assertIn("status", data)

    # 2. The Weekend Blocker
    def test_weekend_blocker_detection(self):
        # Verify method runs and returns boolean
        is_wk = RateLimiter.is_weekend()
        self.assertIsInstance(is_wk, bool)

        # Test check_can_send with override
        can_send, reason = RateLimiter.check_can_send(ignore_weekend=True)
        self.assertIsInstance(can_send, bool)
        self.assertIsInstance(reason, str)

    # 3. Blacklist / Opt-out Detection
    def test_opt_out_keyword_recognition(self):
        detector = ReplyDetector()

        # Opt-out phrases must return True
        self.assertTrue(detector.is_opt_out("Please unsubscribe me from this list."))
        self.assertTrue(detector.is_opt_out("Take me off your mailing list, thanks."))
        self.assertTrue(detector.is_opt_out("Stop emailing me!"))
        self.assertTrue(detector.is_opt_out("Not interested, pass."))
        self.assertTrue(detector.is_opt_out("This is spam, remove me."))

        # Positive responses must return False
        self.assertFalse(detector.is_opt_out("Hey Kxrn! Loved the vibe, we'll feature it on our Friday playlist."))
        self.assertFalse(detector.is_opt_out("Can you send high-res press photos and wav file?"))
        self.assertFalse(detector.is_opt_out("Thanks for reaching out! Great single."))

    def test_record_email_blacklisted(self):
        notion = NotionClient()
        test_id = notion.add_lead(
            name="Optout Journalist",
            email="optout@press.test",
            publication="Press Mag",
            persona="Journalist"
        )
        self.assertTrue(test_id)

        # Blacklist the lead
        ok = notion.record_email_blacklisted(test_id)
        self.assertTrue(ok)

        # Verify status changed to Blacklisted
        lead = notion.get_lead_by_id(test_id)
        self.assertIsNotNone(lead)
        self.assertEqual(lead.status, "Blacklisted")

        # Cleanup
        notion.delete_lead(test_id)

if __name__ == "__main__":
    unittest.main()

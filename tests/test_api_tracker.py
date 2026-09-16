import unittest
from starlette.testclient import TestClient
from api.index import app, TRANSPARENT_PNG_BYTES

class TestTrackerAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")

    def test_tracking_pixel(self):
        resp = self.client.get("/t/test_lead_001.png")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "image/png")
        self.assertEqual(resp.content, TRANSPARENT_PNG_BYTES)
        self.assertIn("no-store", resp.headers.get("cache-control", ""))

if __name__ == "__main__":
    unittest.main()

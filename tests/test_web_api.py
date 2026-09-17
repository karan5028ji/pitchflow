import unittest
from starlette.testclient import TestClient
from api.index import app
from src.config_store import ConfigStore

class TestWebAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_ui_serves_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("PitchFlow", resp.text)
        self.assertIn("<!DOCTYPE html>", resp.text)

    def test_get_and_update_config(self):
        # 1. Get config
        get_res = self.client.get("/api/config")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertIn("sender_name", data)

        # 2. Update config
        post_res = self.client.post("/api/config", json={"sender_name": "Kxrn Tester"})
        self.assertEqual(post_res.status_code, 200)
        updated = post_res.json()
        self.assertEqual(updated["status"], "success")

        # 3. Verify in store
        conf = ConfigStore.load()
        self.assertEqual(conf["sender_name"], "Kxrn Tester")

    def test_leads_endpoints(self):
        # 1. List leads
        res = self.client.get("/api/leads")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("leads", data)
        self.assertIn("summary", data)

        # 2. Create lead
        create_res = self.client.post("/api/leads", json={
            "name": "API Test Curator",
            "email": "api.test@curator.com",
            "publication": "API Music",
            "persona": "Journalist",
            "recent_work": "testing music api"
        })
        self.assertEqual(create_res.status_code, 200)
        lead_id = create_res.json()["id"]

        # 3. Update lead
        patch_res = self.client.patch(f"/api/leads/{lead_id}", json={
            "recent_work": "updated work description"
        })
        self.assertEqual(patch_res.status_code, 200)

        # 4. Delete lead
        del_res = self.client.delete(f"/api/leads/{lead_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_preview_endpoint(self):
        res = self.client.post("/api/preview", json={
            "template_type": "blog",
            "track_name": "Delhi Nights"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("subject", data)
        self.assertIn("html_body", data)
        self.assertIn("Delhi Nights", data["subject"])

    def test_csv_text_import(self):
        import time
        uid = int(time.time() * 1000)
        csv_text = (
            "Name,Email,Publication,Persona,Recent Work\n"
            f"Test Curator 1,curator1_{uid}@music.test,Beat Mag,Journalist,new beats\n"
            f"Test Curator 2,curator2_{uid}@music.test,Chill Playlist,Playlist Curator,lo-fi vibe\n"
        )
        res = self.client.post("/api/leads/import-csv", json={"csv_content": csv_text})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["imported"], 2)

if __name__ == "__main__":
    unittest.main()

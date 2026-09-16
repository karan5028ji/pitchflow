import unittest
from src.crm.schemas import Lead
from src.engine.personalizer import Personalizer

class TestPersonalizer(unittest.TestCase):
    def test_personalizer_variable_injection(self):
        lead = Lead(
            id="lead_123",
            name="Aarav Mehta",
            email="aarav@rollingstone.in",
            publication="Rolling Stone India",
            persona="Journalist",
            recent_work="modern underground hip-hop in Delhi"
        )

        template = (
            "Subject: Music Pitch: {{Track_Name}}\n\n"
            "Hey {{First_Name}},\n\n"
            "Loved your coverage on {{Publication}}, particularly {{Recent_Article}}."
        )

        subject, text_body, html_body = Personalizer.render(
            template_str=template,
            lead=lead,
            extra_vars={"track_name": "Delhi Nights"},
            inject_pixel=True
        )

        self.assertEqual(subject, "Music Pitch: Delhi Nights")
        self.assertIn("Hey Aarav,", text_body)
        self.assertIn("Rolling Stone India", text_body)
        self.assertIn("modern underground hip-hop in Delhi", text_body)
        self.assertIn("/t/lead_123.png", html_body)
        self.assertIn("<img", html_body)

    def test_personalizer_fallbacks(self):
        lead = Lead(
            id="lead_456",
            name="Priya",
            email="priya@test.com",
            publication="",
            persona="Journalist",
            recent_work=None
        )

        template = (
            "Subject: Hello\n\n"
            "Hi {{First_Name}}, checking out {{Publication}} and {{Recent_Article}}."
        )

        subject, text_body, html_body = Personalizer.render(
            template_str=template,
            lead=lead,
            inject_pixel=False
        )

        self.assertIn("Hi Priya,", text_body)
        self.assertIn("your platform", text_body)
        self.assertIn("the latest independent music releases", text_body)
        self.assertNotIn("/t/lead_456.png", html_body)

if __name__ == "__main__":
    unittest.main()

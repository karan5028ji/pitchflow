import unittest
from src.engine.spintax import SpintaxParser

class TestSpintaxParser(unittest.TestCase):
    def test_no_spintax(self):
        text = "Hello world, this is a plain message."
        self.assertEqual(SpintaxParser.spin(text), text)

    def test_simple_spintax(self):
        text = "{Hey|Hi|Hello} there!"
        results = set()
        for _ in range(50):
            res = SpintaxParser.spin(text)
            self.assertIn(res, ["Hey there!", "Hi there!", "Hello there!"])
            results.add(res)
        self.assertEqual(len(results), 3)

    def test_nested_spintax(self):
        text = "{A|{B|C}}"
        results = set()
        for _ in range(50):
            res = SpintaxParser.spin(text)
            self.assertIn(res, ["A", "B", "C"])
            results.add(res)
        self.assertEqual(len(results), 3)

    def test_multiple_spintax_blocks(self):
        text = "{Hi|Hey} {John|Jack}, {how are you|hope you are well}."
        res = SpintaxParser.spin(text)
        self.assertNotIn("{", res)
        self.assertNotIn("}", res)
        self.assertNotIn("|", res)

if __name__ == "__main__":
    unittest.main()

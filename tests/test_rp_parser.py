import unittest
from pathlib import Path

from src.rp_parser import parse_rp


RP_MATTHEW = (
    Path(__file__).resolve().parents[1]
    / "sources"
    / "robinson-pierpont"
    / "tei-xml-unicode"
    / "no-accents"
    / "MAT.xml"
)


class TestRPParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = parse_rp(RP_MATTHEW)

    def test_matthew_1_1(self):
        actual = [
            item["word"]
            for item in self.words
            if item["chapter"] == 1 and item["verse"] == 1
        ]

        self.assertEqual(
            actual,
            [
                "βιβλος",
                "γενεσεως",
                "ιησου",
                "χριστου",
                "υιου",
                "δαυιδ",
                "υιου",
                "αβρααμ",
            ],
        )

    def test_chapter_transition(self):
        first_word = next(
            item for item in self.words
            if item["chapter"] == 2 and item["verse"] == 1
        )

        self.assertEqual(first_word["word"], "του")

    def test_all_chapters_present(self):
        chapters = {item["chapter"] for item in self.words}

        self.assertEqual(chapters, set(range(1, 29)))

    def test_every_word_has_reference(self):
        for item in self.words:
            self.assertIsInstance(item["chapter"], int)
            self.assertIsInstance(item["verse"], int)
            self.assertGreater(item["chapter"], 0)
            self.assertGreater(item["verse"], 0)


if __name__ == "__main__":
    unittest.main()

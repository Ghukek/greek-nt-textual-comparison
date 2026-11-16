import unittest
from pathlib import Path

from src.sr_parser import parse_sr


SR_ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "sources"
    / "statistical-restoration"
    / "SR usfm.zip"
)


class TestSRParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = parse_sr(SR_ARCHIVE)

    def test_matthew_1_1(self):
        actual = [
            item["word"]
            for item in self.words
            if item["chapter"] == 1 and item["verse"] == 1
        ]

        self.assertEqual(
            actual,
            [
                "Βίβλος",
                "γενέσεως",
                "Ἰησοῦ",
                "Χριστοῦ",
                "υἱοῦ",
                "Δαυὶδ",
                "υἱοῦ",
                "Ἀβραάμ",
            ],
        )

    def test_chapter_transition(self):
        first_word = next(
            item for item in self.words
            if item["chapter"] == 2 and item["verse"] == 1
        )

        self.assertEqual(first_word["word"], "Τοῦ")

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

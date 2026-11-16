import unittest

from src.normalization import normalize_word


class TestNormalization(unittest.TestCase):
    def test_greek_normalization(self):
        self.assertEqual(normalize_word("Ἰησοῦ"), "ιησου")
        self.assertEqual(normalize_word("ιησου"), "ιησου")
        self.assertEqual(normalize_word("λόγος"), "λογοσ")
        self.assertEqual(normalize_word("λογοσ"), "λογοσ")
        self.assertEqual(normalize_word("Δαυὶδ"), "δαυιδ")

    def test_additional_greek_forms(self):
        self.assertEqual(normalize_word("Βίβλος"), "βιβλοσ")
        self.assertEqual(normalize_word("γενέσεως"), "γενεσεωσ")
        self.assertEqual(normalize_word("Χριστοῦ"), "χριστου")
        self.assertEqual(normalize_word("δαυιδ"), "δαυιδ")

if __name__ == "__main__":
    unittest.main()

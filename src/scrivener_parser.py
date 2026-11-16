import re
import xml.etree.ElementTree as ET
from pathlib import Path


BOOK_NAMES = {
    "Matt": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Rom": "ROM",
    "iCor": "1CO",
    "iiCor": "2CO",
    "Gal": "GAL",
    "Eph": "EPH",
    "Phil": "PHP",
    "Col": "COL",
    "iThess": "1TH",
    "iiThess": "2TH",
    "iTim": "1TI",
    "iiTim": "2TI",
    "Titus": "TIT",
    "Phlm": "PHM",
    "Heb": "HEB",
    "Jas": "JAS",
    "iPet": "1PE",
    "iiPet": "2PE",
    "iJohn": "1JN",
    "iiJohn": "2JN",
    "iiiJohn": "3JN",
    "Jude": "JUD",
    "Rev": "REV",
}


def parse_scrivener(path, book=None):
    words = []
    root = ET.parse(Path(path)).getroot()

    for marker in root.iter("scripture"):
        match = re.fullmatch(r"(.+?)\s+(\d+):(\d+)", marker.get("passage", ""))
        if not match:
            continue

        book_name, chapter, verse = match.groups()
        book_code = BOOK_NAMES.get(book_name)

        if book_code is None:
            raise ValueError(f"Unknown Scrivener book name: {book_name}")

        if book and book_code != book:
            continue

        sup = marker.getnext() if hasattr(marker, "getnext") else None
        if sup is None:
            raise ValueError(f"Could not locate verse text after {marker.get('passage')}")

        text = sup.tail or ""

        for word in text.split():
            words.append({
                "word": word,
                "chapter": int(chapter),
                "verse": int(verse),
            })

    return words

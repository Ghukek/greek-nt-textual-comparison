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

    for paragraph in root.iter("p"):
        children = list(paragraph)

        for i, marker in enumerate(children):
            if marker.tag != "scripture":
                continue

            match = re.fullmatch(
                r"(.+?)\s+(\d+):(\d+)",
                marker.get("passage", ""),
            )
            if not match:
                continue

            book_name, chapter, verse = match.groups()
            book_code = BOOK_NAMES.get(book_name)

            if book_code is None:
                raise ValueError(
                    f"Unknown Scrivener book name: {book_name}"
                )

            if book and book_code != book:
                continue

            if i + 1 >= len(children) or children[i + 1].tag != "sup":
                raise ValueError(
                    f"Could not locate verse number after "
                    f"{marker.get('passage')}"
                )

            text = children[i + 1].tail or ""

            for word in text.split():
                words.append({
                    "word": word,
                    "chapter": int(chapter),
                    "verse": int(verse),
                })

    return words

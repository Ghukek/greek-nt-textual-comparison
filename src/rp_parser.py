import re
import xml.etree.ElementTree as ET
from pathlib import Path


TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def parse_rp(path):
    words = []
    root = ET.parse(Path(path)).getroot()

    for verse_element in root.findall(".//tei:ab", TEI_NS):
        verse_id = verse_element.get("n", "")
        match = re.fullmatch(r"B\d+K(\d+)V(\d+)", verse_id)

        if not match:
            raise ValueError(f"Unexpected verse ID: {verse_id!r}")

        chapter = int(match.group(1))
        verse = int(match.group(2))

        for word_element in verse_element.findall("tei:w", TEI_NS):
            if word_element.text is None:
                raise ValueError(f"Empty word in verse {verse_id}")

            words.append({
                "word": word_element.text,
                "chapter": chapter,
                "verse": verse,
            })

    return words

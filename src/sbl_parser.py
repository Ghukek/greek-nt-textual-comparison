import re
import xml.etree.ElementTree as ET


def parse_sblgnt(xml_path):
    words = []
    chapter = None
    verse = None

    root = ET.parse(xml_path).getroot()

    for paragraph in root.iter("p"):
        pending_word = None

        for element in paragraph:
            if element.tag == "verse-number":
                reference = element.get("id")
                match = re.search(r"\s+(\d+):(\d+)$", reference or "")

                if not match:
                    raise ValueError(
                        f"Invalid verse reference: {reference!r}"
                    )

                chapter = int(match.group(1))
                verse = int(match.group(2))

            elif element.tag == "w":
                if chapter is None or verse is None:
                    raise ValueError(
                        "Word found without chapter/verse"
                    )

                pending_word = {
                    "word": element.text or "",
                    "chapter": chapter,
                    "verse": verse,
                }
                words.append(pending_word)

            elif element.tag == "suffix" and pending_word is not None:
                pending_word["word"] += (element.text or "").rstrip()
                pending_word = None

    return words


import re
from pathlib import Path


def parse_ght(path):
    words = []
    chapter = None
    verse = None

    with Path(path).open(encoding="utf-8") as source:
        for line in source:
            line = line.strip()

            chapter_match = re.match(r"\\c\s+(\d+)", line)
            if chapter_match:
                chapter = int(chapter_match.group(1))
                verse = None
                continue

            verse_match = re.match(r"\\v\s+(\d+)\s*(.*)", line)
            if verse_match:
                verse = int(verse_match.group(1))
                text = verse_match.group(2)

                for word in text.split():
                    words.append({
                        "word": word,
                        "chapter": chapter,
                        "verse": verse,
                    })

    return words

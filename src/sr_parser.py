import re
import zipfile
from pathlib import Path


def parse_sr(archive_path, member="41-MAT.usfm"):
    words = []
    chapter = None
    verse = None

    with zipfile.ZipFile(archive_path) as archive:
        text = archive.read(member).decode("utf-8")

    for line in text.splitlines():
        line = line.strip()

        chapter_match = re.match(r"\\c\s+(\d+)", line)
        if chapter_match:
            chapter = int(chapter_match.group(1))
            verse = None
            continue

        verse_match = re.match(r"\\v\s+(\d+)", line)
        if verse_match:
            verse = int(verse_match.group(1))
            continue

        for match in re.finditer(
            r"˚?\\w\s+([^|\\\s]+)\|",
            line,
        ):
            if chapter is None or verse is None:
                raise ValueError(
                    f"Word found without chapter/verse: {line!r}"
                )

            words.append({
                "word": match.group(1),
                "chapter": chapter,
                "verse": verse,
            })

    return words

import json
from pathlib import Path


def parse_tr(path, book=None):
    words = []

    with Path(path).open(encoding="utf-8") as source:
        entries = json.load(source)

    for entry in entries:
        if book and entry["book_name_short"] != book:
            continue

        for item in entry["words"]:
            words.append({
                "word": item["greek"],
                "chapter": entry["chapter"],
                "verse": entry["verse"],
            })

    return words

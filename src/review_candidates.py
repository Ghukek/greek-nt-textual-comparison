import json
import difflib
import hashlib
from pathlib import Path

from src.ght_parser import parse_ght
from src.rp_parser import parse_rp
from src.tr_parser import parse_tr
from src.sr_parser import parse_sr
from tests.test_normalization import normalize_word


root = Path("sources")

books = {
    "MAT": ("40MATGHTG.usfm", "MAT.xml", "41-MAT.usfm"),
    "MRK": ("41MRKGHTG.usfm", "MAR.xml", "42-MRK.usfm"),
    "LUK": ("42LUKGHTG.usfm", "LUK.xml", "43-LUK.usfm"),
    "JHN": ("43JHNGHTG.usfm", "JOH.xml", "44-JHN.usfm"),
    "ACT": ("44ACTGHTG.usfm", "ACT.xml", "45-ACT.usfm"),
    "ROM": ("45ROMGHTG.usfm", "ROM.xml", "46-ROM.usfm"),
    "1CO": ("461COGHTG.usfm", "1CO.xml", "47-1CO.usfm"),
    "2CO": ("472COGHTG.usfm", "2CO.xml", "48-2CO.usfm"),
    "GAL": ("48GALGHTG.usfm", "GAL.xml", "49-GAL.usfm"),
    "EPH": ("49EPHGHTG.usfm", "EPH.xml", "50-EPH.usfm"),
    "PHP": ("50PHPGHTG.usfm", "PHP.xml", "51-PHP.usfm"),
    "COL": ("51COLGHTG.usfm", "COL.xml", "52-COL.usfm"),
    "1TH": ("521THGHTG.usfm", "1TH.xml", "53-1TH.usfm"),
    "2TH": ("532THGHTG.usfm", "2TH.xml", "54-2TH.usfm"),
    "1TI": ("541TIGHTG.usfm", "1TI.xml", "55-1TI.usfm"),
    "2TI": ("552TIGHTG.usfm", "2TI.xml", "56-2TI.usfm"),
    "TIT": ("56TITGHTG.usfm", "TIT.xml", "57-TIT.usfm"),
    "PHM": ("57PHMGHTG.usfm", "PHM.xml", "58-PHM.usfm"),
    "HEB": ("58HEBGHTG.usfm", "HEB.xml", "59-HEB.usfm"),
    "JAS": ("59JASGHTG.usfm", "JAM.xml", "60-JAS.usfm"),
    "1PE": ("601PEGHTG.usfm", "1PE.xml", "61-1PE.usfm"),
    "2PE": ("612PEGHTG.usfm", "2PE.xml", "62-2PE.usfm"),
    "1JN": ("621JNGHTG.usfm", "1JO.xml", "63-1JN.usfm"),
    "2JN": ("632JNGHTG.usfm", "2JO.xml", "64-2JN.usfm"),
    "3JN": ("643JNGHTG.usfm", "3JO.xml", "65-3JN.usfm"),
    "JUD": ("65JUDGHTG.usfm", "JUD.xml", "66-JUD.usfm"),
    "REV": ("66REVGHTG.usfm", "REV.xml", "67-REV.usfm"),
}

sources = {}

for book, (ght_file, rp_file, sr_file) in books.items():
    sources[book] = {
        "GHT": parse_ght(root / "ght" / "ghtg_usfm" / ght_file),
        "RP": parse_rp(
            root / "robinson-pierpont" / "tei-xml-unicode"
            / "no-accents" / rp_file
        ),
        "TR": parse_tr(
            root / "textus-receptus" / "data" / "gnt.flat.json",
            book=book,
        ),
        "SR": parse_sr(
            root / "statistical-restoration" / "SR usfm.zip",
            member=sr_file,
        ),
    }

    print(f"Loaded {book}")

def describe(words, start, end):
    selected = words[start:end]

    if not selected:
        return "(no words)"

    first = selected[0]
    last = selected[-1]

    reference = (
        f"{first['chapter']}:{first['verse']}"
        if (first["chapter"], first["verse"])
        == (last["chapter"], last["verse"])
        else (
            f"{first['chapter']}:{first['verse']}"
            f"-{last['chapter']}:{last['verse']}"
        )
    )

    text = " ".join(item["word"] for item in selected)
    return f"{reference}  {text}"


def candidate_regions(words_a, words_b, merge_gap=3):
    normalized_a = [normalize_word(item["word"]) for item in words_a]
    normalized_b = [normalize_word(item["word"]) for item in words_b]

    matcher = difflib.SequenceMatcher(
        None, normalized_a, normalized_b, autojunk=False
    )

    regions = []

    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue

        if regions:
            previous = regions[-1]
            a_gap = a_start - previous[1]
            b_gap = b_start - previous[3]

            if (
                a_gap == b_gap
                and 0 <= a_gap <= merge_gap
                #and a_start - previous[0] <= 12
                #and b_start - previous[2] <= 12
            ):
                previous[1] = a_end
                previous[3] = b_end
                continue

        regions.append([a_start, a_end, b_start, b_end])

    return regions


def candidate_records(book, name_a, words_a, name_b, words_b, context=5, merge_gap=3):
    regions = candidate_regions(words_a, words_b, merge_gap)

    def candidate_id(a_start, a_end, b_start, b_end):
        identity = {
            "book": book,
            "source_a": name_a,
            "source_b": name_b,
            "source_a_start_index": a_start,
            "source_b_start_index": b_start,
            "source_a_start_reference": (
                [words_a[a_start]["chapter"], words_a[a_start]["verse"]]
                if a_start < a_end else None
            ),
            "source_b_start_reference": (
                [words_b[b_start]["chapter"], words_b[b_start]["verse"]]
                if b_start < b_end else None
            ),
            "source_a_region": [
                normalize_word(item["word"])
                for item in words_a[a_start:a_end]
            ],
            "source_b_region": [
                normalize_word(item["word"])
                for item in words_b[b_start:b_end]
            ],
        }
        encoded = json.dumps(
            identity, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]

    records = []

    for a_start, a_end, b_start, b_end in regions:
        if a_start == a_end:
            candidate_type = "insert"
        elif b_start == b_end:
            candidate_type = "delete"
        else:
            candidate_type = "replace"

        records.append({
            "book": book,
            "source_a": name_a,
            "source_b": name_b,
            "type": candidate_type,
            "id": candidate_id(a_start, a_end, b_start, b_end),
            "source_a_region": [
                item["word"] for item in words_a[a_start:a_end]
            ],
            "source_b_region": [
                item["word"] for item in words_b[b_start:b_end]
            ],
            "source_a_start_reference": (
                [words_a[a_start]["chapter"], words_a[a_start]["verse"]]
                if a_start < a_end else None
            ),
            "source_a_end_reference": (
                [words_a[a_end - 1]["chapter"], words_a[a_end - 1]["verse"]]
                if a_start < a_end else None
            ),
            "source_b_start_reference": (
                [words_b[b_start]["chapter"], words_b[b_start]["verse"]]
                if b_start < b_end else None
            ),
            "source_b_end_reference": (
                [words_b[b_end - 1]["chapter"], words_b[b_end - 1]["verse"]]
                if b_start < b_end else None
            ),
            "source_a_context_before": [
                item["word"]
                for item in words_a[max(0, a_start - context):a_start]
            ],
            "source_a_context_after": [
                item["word"]
                for item in words_a[a_end:a_end + context]
            ],
            "source_b_context_before": [
                item["word"]
                for item in words_b[max(0, b_start - context):b_start]
            ],
            "source_b_context_after": [
                item["word"]
                for item in words_b[b_end:b_end + context]
            ],
        })

    return records



def review_pair(name_a, words_a, name_b, words_b, context=5, merge_gap=3):
    regions = candidate_regions(words_a, words_b, merge_gap)

    print(f"\n{'=' * 72}")
    print(f"{name_a} vs {name_b}")
    print(f"{'=' * 72}")

    for number, (a_start, a_end, b_start, b_end) in enumerate(
        regions, start=1
    ):
        print(f"\nCandidate {number}")

        print(
            f"{name_a} context: "
            f"{describe(words_a, max(0, a_start - context), a_start)}"
        )
        print(f"{name_a} region: {describe(words_a, a_start, a_end)}")
        print(
            f"{name_a} context: "
            f"{describe(words_a, a_end, min(len(words_a), a_end + context))}"
        )

        print(
            f"{name_b} context: "
            f"{describe(words_b, max(0, b_start - context), b_start)}"
        )
        print(f"{name_b} region: {describe(words_b, b_start, b_end)}")
        print(
            f"{name_b} context: "
            f"{describe(words_b, b_end, min(len(words_b), b_end + context))}"
        )

    print(f"\nTotal candidate regions: {len(regions)}")



all_candidates = []

pairs = [
    ("GHT", "RP"),
    ("GHT", "TR"),
    ("GHT", "SR"),
    ("RP", "TR"),
    ("RP", "SR"),
    ("TR", "SR"),
]

for book in books:
    for name_a, name_b in pairs:
        candidates = candidate_records(
            book,
            name_a,
            sources[book][name_a],
            name_b,
            sources[book][name_b],
        )
        all_candidates.extend(candidates)

        print(f"{book} {name_a} vs {name_b}: {len(candidates)} candidates")

report_dir = Path("reports")
report_dir.mkdir(exist_ok=True)

report_path = report_dir / "candidates.json"
report_path.write_text(
    json.dumps(all_candidates, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print(f"\nSaved {len(all_candidates)} candidates to {report_path}")

import json
from pathlib import Path

from src.ght_parser import parse_ght
from src.rp_parser import parse_rp
from src.sr_parser import parse_sr
from src.tr_parser import parse_tr
from src.sbl_parser import parse_sblgnt
from src.scrivener_parser import parse_scrivener


ROOT = Path("sources")
REPORTS = Path("reports")

BOOKS = {
    "MAT": ("40MATGHTG.usfm", "MAT.xml", "41-MAT.usfm", "Matt.xml"),
    "MRK": ("41MRKGHTG.usfm", "MAR.xml", "42-MRK.usfm", "Mark.xml"),
    "LUK": ("42LUKGHTG.usfm", "LUK.xml", "43-LUK.usfm", "Luke.xml"),
    "JHN": ("43JHNGHTG.usfm", "JOH.xml", "44-JHN.usfm", "John.xml"),
    "ACT": ("44ACTGHTG.usfm", "ACT.xml", "45-ACT.usfm", "Acts.xml"),
    "ROM": ("45ROMGHTG.usfm", "ROM.xml", "46-ROM.usfm", "Rom.xml"),
    "1CO": ("461COGHTG.usfm", "1CO.xml", "47-1CO.usfm", "1Cor.xml"),
    "2CO": ("472COGHTG.usfm", "2CO.xml", "48-2CO.usfm", "2Cor.xml"),
    "GAL": ("48GALGHTG.usfm", "GAL.xml", "49-GAL.usfm", "Gal.xml"),
    "EPH": ("49EPHGHTG.usfm", "EPH.xml", "50-EPH.usfm", "Eph.xml"),
    "PHP": ("50PHPGHTG.usfm", "PHP.xml", "51-PHP.usfm", "Phil.xml"),
    "COL": ("51COLGHTG.usfm", "COL.xml", "52-COL.usfm", "Col.xml"),
    "1TH": ("521THGHTG.usfm", "1TH.xml", "53-1TH.usfm", "1Thess.xml"),
    "2TH": ("532THGHTG.usfm", "2TH.xml", "54-2TH.usfm", "2Thess.xml"),
    "1TI": ("541TIGHTG.usfm", "1TI.xml", "55-1TI.usfm", "1Tim.xml"),
    "2TI": ("552TIGHTG.usfm", "2TI.xml", "56-2TI.usfm", "2Tim.xml"),
    "TIT": ("56TITGHTG.usfm", "TIT.xml", "57-TIT.usfm", "Titus.xml"),
    "PHM": ("57PHMGHTG.usfm", "PHM.xml", "58-PHM.usfm", "Phlm.xml"),
    "HEB": ("58HEBGHTG.usfm", "HEB.xml", "59-HEB.usfm", "Heb.xml"),
    "JAS": ("59JASGHTG.usfm", "JAM.xml", "60-JAS.usfm", "Jas.xml"),
    "1PE": ("601PEGHTG.usfm", "1PE.xml", "61-1PE.usfm", "1Pet.xml"),
    "2PE": ("612PEGHTG.usfm", "2PE.xml", "62-2PE.usfm", "2Pet.xml"),
    "1JN": ("621JNGHTG.usfm", "1JO.xml", "63-1JN.usfm", "1John.xml"),
    "2JN": ("632JNGHTG.usfm", "2JO.xml", "64-2JN.usfm", "2John.xml"),
    "3JN": ("643JNGHTG.usfm", "3JO.xml", "65-3JN.usfm", "3John.xml"),
    "JUD": ("65JUDGHTG.usfm", "JUD.xml", "66-JUD.usfm", "Jude.xml"),
    "REV": ("66REVGHTG.usfm", "REV.xml", "67-REV.usfm", "Rev.xml"),
}


def load_sources():
    sources = {}

    for book, (ght_file, rp_file, sr_file, sbl_file) in BOOKS.items():
        sources[book] = {
            "GHT": parse_ght(
                ROOT / "ght" / "ghtg_usfm" / ght_file
            ),
            "RP": parse_rp(
                ROOT / "robinson-pierpont" / "tei-xml-unicode"
                / "no-accents" / rp_file
            ),
            "TR": parse_scrivener(
                ROOT / "Scrivener" / "gntscr.xml",
                book=book,
            ),
            "ST": parse_tr(
                ROOT / "textus-receptus" / "data" / "gnt.flat.json",
                book=book,
            ),
            "SR": parse_sr(
                ROOT / "statistical-restoration" / "SR usfm.zip",
                member=sr_file,
            ),
            "SBL": parse_sblgnt(
                ROOT / "SBLGNT" / "data" / "sblgnt" / "xml" / sbl_file
            ),
        }

    return sources


SOURCE_PAIRS = (
    ("GHT", "RP"),
    ("GHT", "TR"),
    ("GHT", "SR"),
    ("GHT", "SBL"),
    ("RP", "TR"),
    ("RP", "SR"),
    ("RP", "SBL"),
    ("TR", "SR"),
    ("TR", "SBL"),
    ("SR", "SBL")
)

EXCLUDED_DECISIONS = {
    "spelling",
    "movable_nu",
    "word_segmentation",
}

COUNT_FIELDS = (
    "words_added",
    "words_removed",
    "words_swapped",
    "transpositions",
)


def load_json(filename):
    with (REPORTS / filename).open(encoding="utf-8") as source:
        return json.load(source)


def make_report_row(book, source_a, source_b, word_count):
    return {
        "book": book,
        "source_a": source_a,
        "source_b": source_b,
        "source_a_word_count": word_count,
        "candidate_units": 0,
        "excluded_units": 0,
        "classified_units": 0,
        "unclassified_units": 0,
        "words_added": 0,
        "words_removed": 0,
        "words_swapped": 0,
        "transpositions": 0,
    }


def finish_report_row(row):
    added = row["words_added"]
    removed = row["words_removed"]
    swapped = row["words_swapped"]
    transpositions = row["transpositions"]
    denominator = row["source_a_word_count"]

    row["textual_variance"] = added + removed + swapped
    row["total_variance"] = (
        row["textual_variance"] + transpositions
    )

    for field in COUNT_FIELDS:
        row[f"{field}_pct"] = (
            row[field] / denominator * 100
            if denominator else None
        )

    row["textual_variance_pct"] = (
        row["textual_variance"] / denominator * 100
        if denominator else None
    )
    row["total_variance_pct"] = (
        row["total_variance"] / denominator * 100
        if denominator else None
    )

    eligible_units = (
        row["classified_units"] + row["unclassified_units"]
    )
    row["classification_coverage_pct"] = (
        row["classified_units"] / eligible_units * 100
        if eligible_units else 0
    )

    return row


def main():
    sources = load_sources()
    candidates = load_json("candidates.json")
    decisions = load_json("decisions.json")
    components = load_json("components.json")

    if isinstance(candidates, dict):
        candidate_items = candidates
    else:
        candidate_items = {
            item["id"]: item for item in candidates
        }

    rows = {}

    for book, texts in sources.items():
        for source_a, source_b in SOURCE_PAIRS:
            key = (book, source_a, source_b)
            rows[key] = make_report_row(
                book,
                source_a,
                source_b,
                len(texts[source_a]),
            )

    for candidate_id, candidate in candidate_items.items():
        key = (
            candidate["book"],
            candidate["source_a"],
            candidate["source_b"],
        )

        if key not in rows:
            continue

        row = rows[key]
        row["candidate_units"] += 1

        decision_entry = decisions.get(candidate_id)
        decision = (
            decision_entry.get("decision")
            if decision_entry else None
        )

        if decision in EXCLUDED_DECISIONS:
            row["excluded_units"] += 1
        elif candidate_id in components:
            component = components[candidate_id]
            row["classified_units"] += 1

            for field in COUNT_FIELDS:
                row[field] += component.get(field, 0)
        else:
            row["unclassified_units"] += 1
#"""
    print("\nUnclassified MRK GHT -> SR candidates:")

    for candidate_id, candidate in candidate_items.items():
        if (
            candidate["book"] != "MRK"
            or candidate["source_a"] != "GHT"
            or candidate["source_b"] != "SR"
        ):
            continue

        decision_entry = decisions.get(candidate_id)
        decision = (
            decision_entry.get("decision")
            if decision_entry else None
        )

        if (
            decision not in EXCLUDED_DECISIONS
            and candidate_id not in components
        ):
            print(
                candidate_id,
                candidate.get("source_a_start_reference"),
                candidate.get("source_b_start_reference"),
                "decision:", decision,
            )
#"""
    book_rows = [
        finish_report_row(row)
        for row in rows.values()
    ]

    nt_rows = []

    for source_a, source_b in SOURCE_PAIRS:
        combined = make_report_row(
            "NT",
            source_a,
            source_b,
            sum(
                row["source_a_word_count"]
                for row in book_rows
                if row["source_a"] == source_a
                and row["source_b"] == source_b
            ),
        )

        for row in book_rows:
            if (
                row["source_a"] != source_a
                or row["source_b"] != source_b
            ):
                continue

            for field in (
                "candidate_units",
                "excluded_units",
                "classified_units",
                "unclassified_units",
                *COUNT_FIELDS,
            ):
                combined[field] += row[field]

        nt_rows.append(finish_report_row(combined))

    report = {
        "books": book_rows,
        "new_testament": nt_rows,
    }

    output_path = REPORTS / "stage3_report.json"
    with output_path.open("w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")

    print(f"Saved {output_path}")
    print(f"Book/source-pair rows: {len(book_rows)}")
    print(f"Combined NT rows: {len(nt_rows)}")

    print("\nCombined New Testament percentages:")
    print(
        f'{"Comparison":<12} '
        f'{"Textual %":>10} {"Total %":>10} '
        f'{"Coverage %":>11}'
    )
    print("-" * 47)

    for row in nt_rows:
        comparison = f'{row["source_a"]} -> {row["source_b"]}'
        print(
            f'{comparison:<12} '
            f'{row["textual_variance_pct"]:>9.3f}% '
            f'{row["total_variance_pct"]:>9.3f}% '
            f'{row["classification_coverage_pct"]:>10.2f}%'
        )

    print("\nIndividual book percentages:")
    print(
        f'{"Book":<6} {"Comparison":<12} '
        f'{"Textual %":>10} {"Total %":>10} '
        f'{"Coverage %":>11}'
    )
    print("-" * 53)

    for row in book_rows:
        comparison = f'{row["source_a"]} -> {row["source_b"]}'
        print(
            f'{row["book"]:<6} {comparison:<12} '
            f'{row["textual_variance_pct"]:>9.3f}% '
            f'{row["total_variance_pct"]:>9.3f}% '
            f'{row["classification_coverage_pct"]:>10.2f}%'
        )

if __name__ == "__main__":
    main()

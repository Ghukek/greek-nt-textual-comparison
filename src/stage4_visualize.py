#!/usr/bin/env python3
"""Phase 4: visualize pairwise textual/total variance as tetrahedra.

Reads reports/stage3_report.json by default. Writes per-book and NT PNGs plus
a combined PDF under reports/phase4 by default. Invalid Euclidean edge sets
are shown using a least-squares 3-D fit, explicitly marked approximate.
"""
import argparse
import json
from pathlib import Path

SOURCES = ("GHT", "RP", "TR", "SR", "SBL")

PAIRS = (
    ("GHT", "RP"),
    ("GHT", "TR"),
    ("GHT", "SR"),
    ("GHT", "SBL"),
    ("RP", "TR"),
    ("RP", "SR"),
    ("RP", "SBL"),
    ("TR", "SR"),
    ("TR", "SBL"),
    ("SR", "SBL"),
)

METRICS = (
    ("textual_variance_pct", "textual"),
    ("total_variance_pct", "total"),
)


def edge_values(rows, book, field):
    selected = {
        (row["source_a"], row["source_b"]): row[field]
        for row in rows if row["book"] == book
    }
    values = {}
    for a, b in PAIRS:
        value = selected.get((a, b))
        if value is None:
            value = selected.get((b, a))
        if value is None:
            raise ValueError(f"Missing {field} edge {a}-{b} for {book}")
        values[(a, b)] = float(value)
    return values

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/stage3_report.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
    )
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as f:
        report = json.load(f)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = report["books"] + report["new_testament"]
    books = []

    for row in report["books"]:
        if row["book"] not in books:
            books.append(row["book"])

    books.append("NT")

    pairs_data = []

    for book in books:
        for field, metric in METRICS:
            edges = edge_values(rows, book, field)

            pairs_data.append({
                "book": book,
                "metric": metric,
                "pairs": [
                    {
                        "source_a": a,
                        "source_b": b,
                        "value": edges[(a, b)],
                    }
                    for a, b in PAIRS
                ],
            })

    output_path = args.output_dir / "pairs.json"
    output_path.write_text(
        json.dumps(pairs_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Exported {len(pairs_data)} book/metric combinations.")
    print(f"Pairwise values per combination: {len(PAIRS)}")
    print(f"JSON: {output_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Phase 4: visualize pairwise textual/total variance as tetrahedra.

Reads reports/stage3_report.json by default. Writes per-book and NT PNGs plus
a combined PDF under reports/phase4 by default. Invalid Euclidean edge sets
are shown using a least-squares 3-D fit, explicitly marked approximate.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from scipy.optimize import least_squares
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation

VERTICES = ("GHT", "RP", "TR", "SR")
PAIRS = (
    ("GHT", "RP"), ("GHT", "TR"), ("GHT", "SR"),
    ("RP", "TR"), ("RP", "SR"), ("TR", "SR"),
)
METRICS = (
    ("textual_variance_pct", "Textual variance (%)", "textual"),
    ("total_variance_pct", "Total variance (%)", "total"),
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


def exact_coordinates(edges):
    # Put GHT at the origin and solve the Gram matrix for RP, TR, SR.
    d = lambda a, b: edges[(a, b)] if (a, b) in edges else edges[(b, a)]
    gram = np.zeros((3, 3), dtype=float)
    for i, si in enumerate(VERTICES[1:]):
        gram[i, i] = d("GHT", si) ** 2
        for j, sj in enumerate(VERTICES[1:]):
            if i != j:
                gram[i, j] = (
                    d("GHT", si) ** 2 + d("GHT", sj) ** 2
                    - d(si, sj) ** 2
                ) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
    valid = bool(np.min(eigenvalues) >= -1e-8 * scale)
    clipped = np.maximum(eigenvalues, 0.0)
    xyz = eigenvectors @ np.diag(np.sqrt(clipped))
    coords = {"GHT": np.zeros(3)}
    for i, name in enumerate(VERTICES[1:]):
        coords[name] = xyz[i, :]
    return coords, valid, eigenvalues


def approximate_coordinates(edges):
    # Optimize four points in 3-D; anchor GHT and remove rigid translation.
    initial, _, _ = exact_coordinates(edges)
    x0 = np.array([initial[v] for v in VERTICES[1:]]).ravel()

    def residual(flat):
        pts = {"GHT": np.zeros(3)}
        for i, name in enumerate(VERTICES[1:]):
            pts[name] = flat[i * 3:(i + 1) * 3]
        return np.array([
            np.linalg.norm(pts[a] - pts[b]) - edges[(a, b)]
            for a, b in PAIRS
        ])

    result = least_squares(residual, x0, max_nfev=5000)
    pts = {"GHT": np.zeros(3)}
    for i, name in enumerate(VERTICES[1:]):
        pts[name] = result.x[i * 3:(i + 1) * 3]
    return pts, residual(result.x)


def optimize_view(coords, edges):
    """Rotate points to make projected edge-length ratios match edge values."""
    points = np.array([coords[v] for v in VERTICES], dtype=float)
    edge_indices = [
        (VERTICES.index(a), VERTICES.index(b))
        for a, b in PAIRS
    ]
    targets = np.array([edges[pair] for pair in PAIRS], dtype=float)

    def score(rotvec):
        rotated = Rotation.from_rotvec(rotvec).apply(points)

        projected = np.array([
            np.linalg.norm(rotated[i, :2] - rotated[j, :2])
            for i, j in edge_indices
        ])

        # Compare ratios after removing the effect of overall drawing scale.
        ratios = projected / np.maximum(targets, 1e-12)
        mean_ratio = max(float(np.mean(ratios)), 1e-12)
        return float(np.mean((ratios / mean_ratio - 1.0) ** 2))

    # Try several starting orientations to reduce local-minimum risk.
    rng = np.random.default_rng(20261116)
    starts = [np.zeros(3)]
    starts.extend(
        rng.uniform(-np.pi, np.pi, size=3)
        for _ in range(24)
    )

    best = None
    for start in starts:
        result = minimize(
            score,
            start,
            method="Powell",
            options={"maxiter": 500, "xtol": 1e-5, "ftol": 1e-8},
        )
        if best is None or result.fun < best.fun:
            best = result

    rotated_points = Rotation.from_rotvec(best.x).apply(points)
    rotated_coords = {
        name: rotated_points[i]
        for i, name in enumerate(VERTICES)
    }

    projected = np.array([
        np.linalg.norm(
            rotated_coords[a][:2] - rotated_coords[b][:2]
        )
        for a, b in PAIRS
    ])
    ratios = projected / np.maximum(targets, 1e-12)
    mean_ratio = max(float(np.mean(ratios)), 1e-12)
    distortion = float(
        np.sqrt(np.mean((ratios / mean_ratio - 1.0) ** 2))
    )

    return rotated_coords, distortion


def make_figure(book, rows, field, metric_title):
    edges = edge_values(rows, book, field)
    coords, valid, eigenvalues = exact_coordinates(edges)
    residuals = None
    if not valid:
        coords, residuals = approximate_coordinates(edges)

    coords, view_distortion = optimize_view(coords, edges)

    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
    points = np.array([coords[v] for v in VERTICES])
    for a, b in PAIRS:
        pa, pb = coords[a], coords[b]
        ax.plot(
            [pa[0], pb[0]], [pa[1], pb[1]],
            linewidth=1.8,
        )
        midpoint = (pa + pb) / 2
        ax.text(
            midpoint[0], midpoint[1],
            f"{edges[(a, b)]:.3f}%",
            fontsize=9, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", alpha=0.88, ec="none"),
        )
    for name in VERTICES:
        p = coords[name]
        ax.scatter([p[0]], [p[1]], s=55)
        ax.text(p[0], p[1], f"  {name}", fontsize=11, weight="bold")

    title = f"{book} — {metric_title}"
    if valid:
        subtitle = "Euclidean tetrahedron: all six edge lengths are geometrically compatible"
    else:
        rms = float(np.sqrt(np.mean(np.square(residuals))))
        subtitle = (
            "Approximate 3-D fit: the six reported values cannot all be exact "
            f"Euclidean edge lengths (edge RMS error {rms:.4f} percentage points)"
        )
    subtitle += (
        f"\nOptimized projected lengths "
        f"(relative RMS distortion: {view_distortion:.1%})"
    )
    ax.set_title(f"{title}\n{subtitle}", fontsize=12, pad=18)

    # Display the optimized projection without 3D-axis distortion.
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    fig.text(
        0.5, 0.01,
        "Edge labels are the original Stage 3 percentages. "
        "Vertex positions have no independent textual-historical meaning.",
        ha="center", fontsize=8,
    )
    return fig, valid, coords, edges


def make_overview(rows, output_path):
    books = []
    seen = set()
    for row in rows:
        if row["book"] != "NT" and row["book"] not in seen:
            seen.add(row["book"])
            books.append(row["book"])
    books.sort(key=lambda b: next(i for i, r in enumerate(rows) if r["book"] == b))
    pairs = [f"{a}–{b}" for a, b in PAIRS]
    fig, axes = plt.subplots(2, 1, figsize=(15, 11), constrained_layout=True)
    for ax, field, title in zip(
        axes,
        ("textual_variance_pct", "total_variance_pct"),
        ("Textual variance (%)", "Total variance (%)"),
    ):
        matrix = []
        for book in books:
            matrix.append([
                next(r[field] for r in rows
                     if r["book"] == book and r["source_a"] == a and r["source_b"] == b)
                for a, b in PAIRS
            ])
        im = ax.imshow(np.array(matrix), aspect="auto", interpolation="nearest")
        ax.set_title(title)
        ax.set_yticks(range(len(books)), books, fontsize=7)
        ax.set_xticks(range(len(pairs)), pairs, rotation=35, ha="right")
        fig.colorbar(im, ax=ax, label="Percent")
    fig.suptitle("New Testament book-by-book pairwise variance", fontsize=15)
    fig.savefig(output_path, dpi=180)
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("reports/stage3_report.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/phase4"))
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

    pdf_path = args.output_dir / "phase4_tetrahedra.pdf"
    manifest = []
    viewer_data = []
    with PdfPages(pdf_path) as pdf:
        for book in books:
            for field, metric_title, slug in METRICS:
                fig, valid, coords, edges = make_figure(
                    book, rows, field, metric_title
                )
                viewer_data.append({
                    "book": book,
                    "metric": slug,
                    "metric_title": metric_title,
                    "exact_euclidean_geometry": valid,
                    "vertices": {
                        name: [float(value) for value in coords[name]]
                        for name in VERTICES
                    },
                    "edges": [
                        {
                            "source_a": a,
                            "source_b": b,
                            "value": edges[(a, b)],
                        }
                        for a, b in PAIRS
                    ],
                })
                png_path = args.output_dir / f"{book.lower()}_{slug}.png"
                fig.savefig(png_path, dpi=180, bbox_inches="tight")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
                manifest.append({
                    "book": book, "metric": slug,
                    "png": png_path.name, "exact_euclidean_geometry": valid,
                })
        overview_path = args.output_dir / "book_pairwise_overview.png"
        fig = make_overview(report["books"], overview_path)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    viewer_path = args.output_dir / "tetrahedra.json"
    viewer_path.write_text(
        json.dumps(viewer_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(manifest)} tetrahedron graphics.")
    print(f"PDF: {pdf_path}")
    print(f"Overview: {overview_path}")
    print(f"Output directory: {args.output_dir}")
    print(
        "Exact Euclidean tetrahedra: "
        f"{sum(x['exact_euclidean_geometry'] for x in manifest)} / {len(manifest)}"
    )
    print(f"Viewer data: {viewer_path}")


if __name__ == "__main__":
    main()

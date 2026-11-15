#!/usr/bin/env python3
"""Compare model-detected nucleus centroids with manual point annotations.

Inputs are Dragonfly centroid CSVs (semicolon-separated, ``PosX``/``PosY``/
``PosZ`` in micrometres). ``PosZ`` identifies the image (Dragonfly stacks the
validation images as slices of one volume).

Two matching modes are available:

``published`` (default)
    The matching used for the validation in Bryton, Correa et al. 2025
    (Fig. S4F-G): a KD-tree nearest-neighbour search with a 15 um match
    radius. Model points with an annotation within the radius are true
    positives, the remaining model points false positives, and annotations
    without a matching model point false negatives.

``per-image``
    Points are matched only within the same image (same ``PosZ``),
    one-to-one with an optimal (Hungarian) assignment, at a radius set with
    ``--radius``. Useful when validating the model on your own data, together
    with ``--pairwise`` to compare annotators with each other.

Reported metrics: precision, recall, F1 and the "accuracy" used in the paper,
which is TP / (TP + FP + FN) (also known as the critical success index).

Usage
-----
    python validate_against_annotations.py --model model.csv \
        --reference rater_B.csv rater_C.csv
    python validate_against_annotations.py --mode per-image --radius 5 \
        --model model.csv --reference rater_B.csv rater_C.csv
    # agreement between annotators:
    python validate_against_annotations.py --pairwise rater_B.csv rater_C.csv
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree


def load(path: Path) -> np.ndarray:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(2048); fh.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        rows = list(csv.DictReader(fh, delimiter=delim))
    pts = [(float(r["PosX"]), float(r["PosY"]), round(float(r.get("PosZ") or 0), 3)) for r in rows]
    return np.asarray(pts, float)


def counts_per_image(test: np.ndarray, ref: np.ndarray, radius: float):
    tp = fp = fn = 0
    shared = sorted(set(test[:, 2]) & set(ref[:, 2]))
    for z in shared:
        a = test[test[:, 2] == z, :2]
        b = ref[ref[:, 2] == z, :2]
        D = np.linalg.norm(a[:, None] - b[None], axis=2)
        cost = np.where(D <= radius, D, 1e9)
        r, c = linear_sum_assignment(cost)
        k = int((cost[r, c] <= radius).sum())
        tp += k; fp += len(a) - k; fn += len(b) - k
    return tp, fp, fn, len(shared)


def counts_published(test: np.ndarray, ref: np.ndarray, radius: float = 15.0):
    d, idx = cKDTree(ref[:, :2]).query(test[:, :2], distance_upper_bound=radius)
    hit = d < radius
    tp = int(hit.sum())
    fp = len(test) - tp
    ref_hit = np.zeros(len(ref), bool); ref_hit[idx[hit]] = True
    fn = len(ref) - int(ref_hit.sum())
    return tp, fp, fn, len(set(ref[:, 2]))


def metrics(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    acc = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    return p, r, f1, acc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", type=Path, help="centroids detected by the model")
    ap.add_argument("--reference", type=Path, nargs="+", help="one CSV per human annotator")
    ap.add_argument("--pairwise", type=Path, nargs="+", help="F1 between every pair of files (per-image mode)")
    ap.add_argument("--mode", choices=["published", "per-image"], default="published")
    ap.add_argument("--radius", type=float, default=5.0, help="match radius in um for per-image mode (default 5)")
    a = ap.parse_args(argv)

    if a.pairwise:
        data = {p.stem: load(p) for p in a.pairwise}
        print(f"pairwise F1, per-image one-to-one matching, radius {a.radius} um")
        for (n1, x), (n2, y) in itertools.combinations(data.items(), 2):
            tp, fp, fn, nz = counts_per_image(x, y, a.radius)
            print(f"  {n1:>12s} vs {n2:<12s} F1={metrics(tp, fp, fn)[2]:.3f}  ({nz} shared images)")
        return 0

    if not (a.model and a.reference):
        ap.error("give --model and --reference, or --pairwise")
    test = load(a.model)
    rows = []
    for ref_path in a.reference:
        ref = load(ref_path)
        if a.mode == "per-image":
            tp, fp, fn, nz = counts_per_image(test, ref, a.radius)
        else:
            tp, fp, fn, nz = counts_published(test, ref)
        p, r, f1, acc = metrics(tp, fp, fn)
        rows.append((ref_path.stem, p, r, f1, acc, tp, fp, fn, nz))

    label = f"per-image, one-to-one, radius {a.radius} um" if a.mode == "per-image" else "published (nearest neighbour, 15 um)"
    print(f"model: {a.model.name}   mode: {label}")
    print(f"{'reference':>12s} {'prec':>6s} {'recall':>6s} {'F1':>6s} {'acc*':>6s} {'TP':>5s} {'FP':>5s} {'FN':>5s} images")
    for name, p, r, f1, acc, tp, fp, fn, nz in rows:
        print(f"{name:>12s} {p:6.3f} {r:6.3f} {f1:6.3f} {acc:6.3f} {tp:5d} {fp:5d} {fn:5d} {nz:3d}")
    arr = np.array([row[1:5] for row in rows])
    if len(rows) > 1:
        m, s = arr.mean(0), arr.std(0)
        print(f"{'mean':>12s} " + " ".join(f"{v:6.3f}" for v in m))
        print(f"{'SD':>12s} " + " ".join(f"{v:6.3f}" for v in s))
    print("* accuracy = TP / (TP + FP + FN), as defined in the paper")
    return 0


if __name__ == "__main__":
    sys.exit(main())

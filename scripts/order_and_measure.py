#!/usr/bin/env python3
"""Order nucleus centroids along a membrane and compute cell count / spacing.

Reads centroid CSV files exported from Dragonfly (``Centroids -> Export -> Data
to file...``; semicolon-separated, columns ``PosX``/``PosY``/``PosZ`` in
micrometres), orders the centroids of each image into a single open path along
the epithelium, and reports:

* cell count           number of centroids in the path
* membrane length      sum of neighbour-to-neighbour distances (um)
* mean cell spacing    mean neighbour-to-neighbour distance (um)
* per-segment metrics  path split into N equal-length segments (default 10):
                       nuclei per segment and mean spacing per segment

This is the post-processing described in Bryton, Correa et al., Sci Rep 15,
40801 (2025), Methods "Raw data processing" and Fig. S4 O-R. The path is built
with a nearest-neighbour heuristic tried from every starting centroid, then
refined with 2-opt.

Orientation: the published analysis ran from the limbal to the strial end for
Reissner's membrane and from posterior to anterior for the saccular membrane.
Which image direction that is depends on how the section was digitised, so
choose it with ``--start-at`` (default: the end with the larger Y value, which
is what the lab's original script used).

Usage
-----
    python order_and_measure.py path/to/centroid_csvs -o results/
    python order_and_measure.py one_file.csv --segments 10 --start-at left --plot
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------- IO


def read_centroids(path: Path) -> dict[float, np.ndarray]:
    """Return {z: (n, 2) array of PosX/PosY} for a Dragonfly centroid CSV."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(2048)
        fh.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        rows = list(csv.DictReader(fh, delimiter=delim))
    if not rows or "PosX" not in rows[0] or "PosY" not in rows[0]:
        raise ValueError(f"{path.name}: no PosX/PosY columns found")
    out: dict[float, list] = {}
    for r in rows:
        try:
            x, y = float(r["PosX"]), float(r["PosY"])
        except (TypeError, ValueError):
            continue
        z = round(float(r.get("PosZ") or 0.0), 3)
        out.setdefault(z, []).append((x, y))
    return {z: np.asarray(v, float) for z, v in sorted(out.items())}


# ------------------------------------------------------------------ ordering


def _path_length(order: np.ndarray, D: np.ndarray) -> float:
    return float(D[order[:-1], order[1:]].sum())


def _nearest_neighbour_path(start: int, D: np.ndarray) -> np.ndarray:
    n = len(D)
    visited = np.zeros(n, bool)
    order = [start]
    visited[start] = True
    for _ in range(n - 1):
        d = np.where(visited, np.inf, D[order[-1]])
        nxt = int(np.argmin(d))
        order.append(nxt)
        visited[nxt] = True
    return np.asarray(order)


def _two_opt(order: np.ndarray, D: np.ndarray, max_passes: int = 50) -> np.ndarray:
    """2-opt for an open path (endpoints may move)."""
    order = order.copy()
    n = len(order)
    for _ in range(max_passes):
        improved = False
        for i in range(0, n - 2):
            a = order[i - 1] if i > 0 else None
            b = order[i]
            for j in range(i + 1, n - 1 if a is None else n):
                c = order[j]
                d = order[j + 1] if j + 1 < n else None
                before = (D[a, b] if a is not None else 0) + (D[c, d] if d is not None else 0)
                after = (D[a, c] if a is not None else 0) + (D[b, d] if d is not None else 0)
                if after + 1e-9 < before:
                    order[i : j + 1] = order[i : j + 1][::-1]
                    improved = True
        if not improved:
            break
    return order


def order_path(xy: np.ndarray, start_at: str = "max-y") -> np.ndarray:
    """Return indices that order ``xy`` into one open path along the membrane."""
    n = len(xy)
    if n < 3:
        order = np.arange(n)
    else:
        D = np.linalg.norm(xy[:, None] - xy[None], axis=2)
        best, best_len = None, np.inf
        for s in range(n):
            o = _nearest_neighbour_path(s, D)
            L = _path_length(o, D)
            if L < best_len:
                best, best_len = o, L
        order = _two_opt(best, D)
    first, last = xy[order[0]], xy[order[-1]]
    flip = {
        "max-y": first[1] < last[1],
        "min-y": first[1] > last[1],
        "left": first[0] > last[0],
        "right": first[0] < last[0],
    }[start_at]
    return order[::-1] if flip else order


# ------------------------------------------------------------------- metrics


def measure(xy_ordered: np.ndarray, n_segments: int) -> dict:
    steps = np.linalg.norm(np.diff(xy_ordered, axis=0), axis=1)
    length = float(steps.sum())
    res = {
        "cell_count": int(len(xy_ordered)),
        "membrane_length_um": length,
        "mean_spacing_um": float(steps.mean()) if len(steps) else float("nan"),
        "sd_spacing_um": float(steps.std(ddof=1)) if len(steps) > 1 else float("nan"),
    }
    # arc-length position of every nucleus, then bin into equal-length segments
    s = np.concatenate([[0.0], np.cumsum(steps)])
    edges = np.linspace(0, length, n_segments + 1)
    seg = np.clip(np.searchsorted(edges, s, side="right") - 1, 0, n_segments - 1)
    mid = (s[:-1] + s[1:]) / 2  # spacing assigned to the segment of its midpoint
    seg_mid = np.clip(np.searchsorted(edges, mid, side="right") - 1, 0, n_segments - 1)
    for k in range(n_segments):
        res[f"seg{k + 1:02d}_count"] = int((seg == k).sum())
        sp = steps[seg_mid == k]
        res[f"seg{k + 1:02d}_spacing_um"] = float(sp.mean()) if len(sp) else float("nan")
    return res, steps


# ---------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", type=Path, help="centroid CSV files or folders containing them")
    ap.add_argument("-o", "--outdir", type=Path, default=None, help="output folder (default: next to each input)")
    ap.add_argument("--segments", type=int, default=10, help="number of equal-length segments (default 10)")
    ap.add_argument("--start-at", choices=["max-y", "min-y", "left", "right"], default="max-y",
                    help="which end of the membrane is position 0 (default max-y)")
    ap.add_argument("--pattern", default="*.csv", help="glob for files inside folders (e.g. '*_ep*.csv')")
    ap.add_argument("--plot", action="store_true", help="save a PNG of each ordered path for review")
    a = ap.parse_args(argv)

    files: list[Path] = []
    for p in a.inputs:
        if p.is_dir():
            files += sorted(f for f in p.glob(a.pattern) if not f.stem.endswith("_ordered"))
        else:
            files.append(p)
    if not files:
        print("no CSV files found", file=sys.stderr)
        return 1

    summary = []
    for f in files:
        try:
            planes = read_centroids(f)
        except ValueError as e:
            print(f"skip: {e}", file=sys.stderr)
            continue
        outdir = a.outdir or f.parent
        outdir.mkdir(parents=True, exist_ok=True)
        ordered_rows = []
        for z, xy in planes.items():
            order = order_path(xy, a.start_at)
            xy_o = xy[order]
            m, steps = measure(xy_o, a.segments)
            summary.append({"file": f.name, "PosZ": z, **m})
            for i, (x, y) in enumerate(xy_o):
                ordered_rows.append({"order": i + 1, "PosX": x, "PosY": y, "PosZ": z,
                                     "neighbor_distance_um": 0.0 if i == 0 else float(steps[i - 1])})
            if a.plot:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(7, 5))
                ax.plot(xy_o[:, 0], xy_o[:, 1], "-", c="0.6", lw=1)
                sc = ax.scatter(xy_o[:, 0], xy_o[:, 1], c=np.arange(len(xy_o)), cmap="viridis", s=12)
                ax.annotate("start", xy_o[0], color="crimson")
                ax.set_aspect("equal"); ax.invert_yaxis()
                ax.set_xlabel("X (um)"); ax.set_ylabel("Y (um)")
                ax.set_title(f"{f.stem}  z={z}  n={len(xy_o)}  L={m['membrane_length_um']:.0f} um")
                fig.colorbar(sc, label="order")
                fig.tight_layout()
                fig.savefig(outdir / f"{f.stem}_z{z}_ordered.png", dpi=150)
                plt.close(fig)
        with open(outdir / f"{f.stem}_ordered.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(ordered_rows[0]), delimiter=";")
            w.writeheader(); w.writerows(ordered_rows)

    out = (a.outdir or files[0].parent) / "summary.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    for r in summary:
        print(f"{r['file']:40s} z={r['PosZ']:<6} n={r['cell_count']:4d}  "
              f"L={r['membrane_length_um']:7.1f} um  spacing={r['mean_spacing_um']:5.1f} um")
    print(f"summary written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

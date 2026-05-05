#!/usr/bin/env python3
"""Extract centerline data from the latest OpenFOAM time directory."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np

GAMMA = 1.4
R_AIR = 287.0


def latest_time(case_dir: Path) -> Path:
    times = []
    for path in case_dir.iterdir():
        if path.is_dir():
            try:
                times.append((float(path.name), path))
            except ValueError:
                pass
    if not times:
        raise FileNotFoundError("No numeric OpenFOAM time directories found")
    return max(times, key=lambda item: item[0])[1]


def list_block_after_header(text: str) -> str:
    header_end = text.index("// * *")
    start = text.index("(", header_end) + 1
    end = text.index("\n)", start)
    return text[start:end]


def read_points(path: Path) -> np.ndarray:
    rows = re.findall(
        r"\(([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)",
        list_block_after_header(path.read_text()),
    )
    return np.array(rows, dtype=float)


def read_faces(path: Path) -> list[list[int]]:
    return [
        [int(v) for v in row.split()]
        for row in re.findall(r"\d+\(([^()]+)\)", list_block_after_header(path.read_text()))
    ]


def read_labels(path: Path) -> np.ndarray:
    return np.fromstring(list_block_after_header(path.read_text()), dtype=int, sep=" ")


def field_count(field_dir: Path) -> int:
    owner = read_labels(field_dir.parent / "constant/polyMesh/owner")
    neighbour = read_labels(field_dir.parent / "constant/polyMesh/neighbour")
    return int(max(owner.max(), neighbour.max())) + 1


def read_scalar_field(path: Path, n_cells: int | None = None) -> np.ndarray:
    text = path.read_text()
    uniform = re.search(r"internalField\s+uniform\s+([-+0-9.eE]+)\s*;", text)
    if uniform:
        if n_cells is None:
            raise ValueError(f"{path} is uniform and n_cells was not provided")
        return np.full(n_cells, float(uniform.group(1)))

    start = text.index("internalField")
    start = text.index("(", start) + 1
    end = text.index("\n)", start)
    return np.fromstring(text[start:end], sep=" ")


def read_vector_field(path: Path, n_cells: int | None = None) -> np.ndarray:
    text = path.read_text()
    uniform = re.search(r"internalField\s+uniform\s+\(([^()]+)\)\s*;", text)
    if uniform:
        if n_cells is None:
            raise ValueError(f"{path} is uniform and n_cells was not provided")
        vec = np.array([float(v) for v in uniform.group(1).split()])
        return np.tile(vec, (n_cells, 1))

    start = text.index("internalField")
    start = text.index("(", start) + 1
    end = text.index("\n)", start)
    rows = re.findall(r"\(([^()]+)\)", text[start:end])
    return np.array([[float(v) for v in row.split()] for row in rows])


def cell_centres(poly_mesh: Path) -> np.ndarray:
    points = read_points(poly_mesh / "points")
    faces = read_faces(poly_mesh / "faces")
    owner = read_labels(poly_mesh / "owner")
    neighbour = read_labels(poly_mesh / "neighbour")
    n_cells = int(max(owner.max(), neighbour.max())) + 1

    centres = np.zeros((n_cells, 3))
    counts = np.zeros(n_cells)
    face_centres = np.array([points[face].mean(axis=0) for face in faces])

    for face_i, cell_i in enumerate(owner):
        centres[cell_i] += face_centres[face_i]
        counts[cell_i] += 1
    for face_i, cell_i in enumerate(neighbour):
        centres[cell_i] += face_centres[face_i]
        counts[cell_i] += 1

    return centres / counts[:, None]


def extract_centerline(centres: np.ndarray, data: dict[str, np.ndarray], bins: int) -> dict[str, np.ndarray]:
    x = centres[:, 0]
    y_abs = np.abs(centres[:, 1])
    edges = np.linspace(x.min(), x.max(), bins + 1)
    out = {"x": [], "Mach": [], "p": [], "T": [], "rho": [], "Umag": []}

    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (x >= lo) & (x < hi)
        if not np.any(mask):
            continue
        ids = np.where(mask)[0]
        near = ids[np.argsort(y_abs[ids])[:2]]
        out["x"].append(centres[near, 0].mean())
        for key in ("Mach", "p", "T", "rho", "Umag"):
            out[key].append(data[key][near].mean())

    return {key: np.array(value) for key, value in out.items()}


def write_centerline(case_dir: Path, time_name: str, out_path: Path, bins: int) -> Path:
    time_dir = latest_time(case_dir) if time_name == "latest" else case_dir / time_name
    poly_mesh = case_dir / "constant/polyMesh"

    owner = read_labels(poly_mesh / "owner")
    neighbour = read_labels(poly_mesh / "neighbour")
    n_cells = int(max(owner.max(), neighbour.max())) + 1

    centres = cell_centres(poly_mesh)
    p = read_scalar_field(time_dir / "p", n_cells)
    T = read_scalar_field(time_dir / "T", n_cells)
    rho = read_scalar_field(time_dir / "rho", n_cells)
    U = read_vector_field(time_dir / "U", n_cells)
    umag = np.linalg.norm(U, axis=1)
    ma_path = time_dir / "Ma"
    mach = read_scalar_field(ma_path, n_cells) if ma_path.exists() else umag / np.sqrt(GAMMA * R_AIR * T)

    centerline = extract_centerline(
        centres,
        {"Mach": mach, "p": p, "T": T, "rho": rho, "Umag": umag},
        bins,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    table = np.column_stack([
        centerline["x"],
        centerline["Mach"],
        centerline["p"],
        centerline["T"],
        centerline["rho"],
        centerline["Umag"],
    ])
    np.savetxt(
        out_path,
        table,
        delimiter=",",
        header="x,Mach,p,T,rho,U_magnitude",
        comments="",
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=Path("."))
    parser.add_argument("--time", default="latest")
    parser.add_argument("--bins", type=int, default=500)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("postProcessing/centerline/centerline_latest.csv"),
    )
    args = parser.parse_args()

    path = write_centerline(args.case.resolve(), args.time, args.case / args.output, args.bins)
    print(f"Wrote centerline CSV: {path}")


if __name__ == "__main__":
    main()

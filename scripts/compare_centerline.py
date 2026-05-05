#!/usr/bin/env python3
"""Compare OpenFOAM centerline data with quasi-1D isentropic nozzle theory."""

from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import numpy as np


GAMMA = 1.4
R_AIR = 287.0

NOZZLE_X = np.array([0.000, 0.012, 0.024, 0.036, 0.045, 0.050,
                     0.055, 0.070, 0.085, 0.100, 0.120])
NOZZLE_HALF_HEIGHT = np.array([0.0200, 0.0185, 0.0155, 0.0122, 0.0104,
                               0.0100, 0.0105, 0.0140, 0.0185, 0.0225,
                               0.0250])


def latest_time(case_dir: Path) -> Path:
    times = []
    for path in case_dir.iterdir():
        if path.is_dir():
            try:
                times.append((float(path.name), path))
            except ValueError:
                pass
    if not times:
        raise FileNotFoundError("No OpenFOAM time directories found")
    return max(times, key=lambda item: item[0])[1]


def data_block(text: str, keyword: str = "internalField") -> str:
    start = text.index(keyword)
    start = text.index("(", start) + 1
    end = text.index("\n)", start)
    return text[start:end]


def read_scalar_field(path: Path) -> np.ndarray:
    text = path.read_text()
    if "internalField   uniform" in text:
        value = float(re.search(r"internalField\s+uniform\s+([^;]+);", text).group(1))
        raise ValueError(f"{path} is uniform; cannot infer cell count for expansion")
    values = np.fromstring(data_block(text), sep=" ")
    return values


def read_vector_field(path: Path) -> np.ndarray:
    text = path.read_text()
    block = data_block(text)
    rows = re.findall(r"\(([^()]+)\)", block)
    return np.array([[float(v) for v in row.split()] for row in rows])


def read_points(path: Path) -> np.ndarray:
    text = path.read_text()
    rows = re.findall(r"\(([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)", data_block(text, "FoamFile"))
    return np.array(rows, dtype=float)


def read_faces(path: Path) -> list[list[int]]:
    text = path.read_text()
    block = data_block(text, "FoamFile")
    return [[int(v) for v in row.split()] for row in re.findall(r"\d+\(([^()]+)\)", block)]


def read_labels(path: Path) -> np.ndarray:
    text = path.read_text()
    return np.fromstring(data_block(text, "FoamFile"), dtype=int, sep=" ")


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


def extract_centerline(centres: np.ndarray, fields: dict[str, np.ndarray], n_bins: int) -> dict[str, np.ndarray]:
    x = centres[:, 0]
    y = np.abs(centres[:, 1])
    bins = np.linspace(x.min(), x.max(), n_bins + 1)

    profile = {"x": [], "p": [], "T": [], "M": []}
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (x >= lo) & (x < hi)
        if not np.any(mask):
            continue
        ids = np.where(mask)[0]
        near = ids[np.argsort(y[ids])[:2]]
        profile["x"].append(centres[near, 0].mean())
        profile["p"].append(fields["p"][near].mean())
        profile["T"].append(fields["T"][near].mean())
        profile["M"].append(fields["M"][near].mean())

    return {key: np.array(value) for key, value in profile.items()}


def area_mach(mach: float, gamma: float) -> float:
    term = (2.0 / (gamma + 1.0)) * (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    exponent = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    return (term ** exponent) / mach


def solve_mach_from_area(area_ratio: float, supersonic: bool, gamma: float) -> float:
    lo, hi = (1.0 + 1e-8, 8.0) if supersonic else (1e-8, 1.0 - 1e-8)
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        value = area_mach(mid, gamma)
        if supersonic:
            if value < area_ratio:
                lo = mid
            else:
                hi = mid
        else:
            if value > area_ratio:
                lo = mid
            else:
                hi = mid
    return 0.5 * (lo + hi)


def isentropic_profile(x: np.ndarray, p0: float, T0: float, p_back: float, gamma: float) -> dict[str, np.ndarray]:
    area = 2.0 * np.interp(x, NOZZLE_X, NOZZLE_HALF_HEIGHT)
    throat_i = int(np.argmin(area))
    a_throat = area[throat_i]
    a_exit = area[-1]

    exit_mach_from_pressure = math.sqrt(
        max(0.0, (2.0 / (gamma - 1.0)) * ((p0 / p_back) ** ((gamma - 1.0) / gamma) - 1.0))
    )
    effective_a_star = a_exit / area_mach(exit_mach_from_pressure, gamma)

    choked = effective_a_star > a_throat
    if choked:
        a_star = a_throat
        mode = "choked-isentropic"
    else:
        a_star = effective_a_star
        mode = "subsonic-isentropic"

    mach = np.empty_like(x)
    for i, a in enumerate(area):
        area_ratio = max(a / a_star, 1.0)
        supersonic = choked and i > throat_i
        mach[i] = solve_mach_from_area(area_ratio, supersonic, gamma)

    temp_ratio = 1.0 / (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    press_ratio = temp_ratio ** (gamma / (gamma - 1.0))
    return {
        "x": x,
        "M": mach,
        "p_ratio": press_ratio,
        "T_ratio": temp_ratio,
        "mode": mode,
        "exit_mach_from_pressure": exit_mach_from_pressure,
    }


def save_plot(x: np.ndarray, cfd_y: np.ndarray, theory_y: np.ndarray, ylabel: str, out_path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.plot(x, cfd_y, label="CFD centerline", linewidth=2)
    plt.plot(x, theory_y, "--", label="1D isentropic", linewidth=2)
    plt.xlabel("x [m]")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=Path("."), help="OpenFOAM case directory")
    parser.add_argument("--time", default="latest", help="Time directory or 'latest'")
    parser.add_argument("--p0", type=float, default=300000.0, help="inlet total pressure [Pa]")
    parser.add_argument("--T0", type=float, default=300.0, help="inlet total temperature [K]")
    parser.add_argument("--p-back", type=float, default=250000.0, help="outlet static pressure [Pa]")
    parser.add_argument("--gamma", type=float, default=GAMMA)
    parser.add_argument("--R", type=float, default=R_AIR)
    parser.add_argument("--bins", type=int, default=500)
    parser.add_argument("--out-dir", type=Path, default=Path("postProcessing/centerlineComparison"))
    args = parser.parse_args()

    case_dir = args.case.resolve()
    time_dir = latest_time(case_dir) if args.time == "latest" else case_dir / args.time
    out_dir = case_dir / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    centres = cell_centres(case_dir / "constant/polyMesh")
    p = read_scalar_field(time_dir / "p")
    T = read_scalar_field(time_dir / "T")
    U = read_vector_field(time_dir / "U")
    mach = np.linalg.norm(U, axis=1) / np.sqrt(args.gamma * args.R * T)

    centerline = extract_centerline(centres, {"p": p, "T": T, "M": mach}, args.bins)
    theory = isentropic_profile(centerline["x"], args.p0, args.T0, args.p_back, args.gamma)

    cfd_p_ratio = centerline["p"] / args.p0
    cfd_t_ratio = centerline["T"] / args.T0

    table = np.column_stack([
        centerline["x"],
        centerline["M"],
        theory["M"],
        cfd_p_ratio,
        theory["p_ratio"],
        cfd_t_ratio,
        theory["T_ratio"],
    ])
    np.savetxt(
        out_dir / "centerline_comparison.csv",
        table,
        delimiter=",",
        header="x,cfd_M,theory_M,cfd_p_p0,theory_p_p0,cfd_T_T0,theory_T_T0",
        comments="",
    )

    save_plot(centerline["x"], centerline["M"], theory["M"], "Mach number [-]", out_dir / "mach_vs_x.png")
    save_plot(centerline["x"], cfd_p_ratio, theory["p_ratio"], "p / p0 [-]", out_dir / "pressure_ratio_vs_x.png")
    save_plot(centerline["x"], cfd_t_ratio, theory["T_ratio"], "T / T0 [-]", out_dir / "temperature_ratio_vs_x.png")

    print(f"Read time directory: {time_dir.relative_to(case_dir)}")
    print(f"Extracted {len(centerline['x'])} centerline stations")
    print(f"1D reference mode: {theory['mode']}")
    if theory["mode"] == "choked-isentropic":
        print("Warning: p_back/p0 is too low for a fully subsonic isentropic solution with this area ratio.")
    print(f"Wrote: {out_dir / 'centerline_comparison.csv'}")
    print(f"Wrote plots in: {out_dir}")


if __name__ == "__main__":
    main()

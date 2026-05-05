#!/usr/bin/env python3
"""Validate centerline Mach number against quasi-1D area-Mach theory."""

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


def area_mach(mach: float | np.ndarray, gamma: float = GAMMA) -> float | np.ndarray:
    term = (2.0 / (gamma + 1.0)) * (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    exponent = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    return term ** exponent / mach


def solve_mach(area_ratio: float, supersonic: bool, gamma: float = GAMMA) -> float:
    if area_ratio < 1.0:
        raise ValueError(f"A/A* must be >= 1, got {area_ratio}")
    if abs(area_ratio - 1.0) < 1e-12:
        return 1.0

    lo, hi = (1.0 + 1e-10, 50.0) if supersonic else (1e-10, 1.0 - 1e-10)
    if supersonic:
        while area_mach(hi, gamma) < area_ratio:
            hi *= 2.0
            if hi > 1e6:
                raise RuntimeError(f"Could not bracket supersonic Mach for A/A*={area_ratio}")

    for _ in range(160):
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


def solve_branch(area_ratio: np.ndarray, supersonic: bool, gamma: float) -> np.ndarray:
    return np.array([solve_mach(float(ratio), supersonic, gamma) for ratio in area_ratio])


def block_contents(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\(", text)
    if not match:
        raise ValueError(f"Could not find '{name}' block")
    start = match.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return text[start : i - 1]


def nozzle_profile(block_mesh_dict: Path) -> tuple[np.ndarray, np.ndarray]:
    text = block_mesh_dict.read_text()
    vertices = re.findall(
        r"\(([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)",
        block_contents(text, "vertices"),
    )
    if not vertices:
        raise ValueError(f"No vertices found in {block_mesh_dict}")

    by_x: dict[float, list[float]] = {}
    for x_raw, y_raw, _ in vertices:
        x = float(x_raw)
        y = abs(float(y_raw))
        by_x.setdefault(x, []).append(y)

    xs = np.array(sorted(by_x))
    half_height = np.array([max(by_x[x]) for x in xs])
    area = 2.0 * half_height
    return xs, area


def interpolate_area(centerline_x: np.ndarray, geom_x: np.ndarray, geom_area: np.ndarray) -> np.ndarray:
    return np.interp(centerline_x, geom_x, geom_area)


def detect_shock_region(x: np.ndarray, mach: np.ndarray, throat_x: float) -> tuple[float | None, np.ndarray]:
    downstream = x > throat_x
    candidates = np.where(downstream & (mach > 0.8))[0]
    if len(candidates) < 3:
        return None, np.zeros_like(x, dtype=bool)

    gradient = np.gradient(mach, x)
    shock_i = candidates[np.argmin(gradient[candidates])]
    if gradient[shock_i] >= -5.0:
        return None, np.zeros_like(x, dtype=bool)

    shock_x = float(x[shock_i])
    width = max(0.006, 0.04 * (float(x.max()) - float(x.min())))
    return shock_x, np.abs(x - shock_x) <= width


def branch_for_case(
    case_name: str,
    x: np.ndarray,
    area_ratio: np.ndarray,
    subsonic_branch: np.ndarray,
    supersonic_branch: np.ndarray,
    throat_x: float,
    mach: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str, float | None, np.ndarray]:
    theory = np.array(subsonic_branch, copy=True)
    valid = np.ones_like(x, dtype=bool)
    shock_x = None
    shock_mask = np.zeros_like(x, dtype=bool)

    if case_name == "subsonic":
        note = "subsonic branch used over the full nozzle"
    elif case_name == "internal_shock":
        theory[x > throat_x] = supersonic_branch[x > throat_x]
        shock_x, shock_mask = detect_shock_region(x, mach, throat_x)
        if shock_x is not None:
            valid &= ~shock_mask
            valid &= ~((x > shock_x) & (mach < 0.95))
            note = (
                "subsonic branch before the throat and supersonic branch after the throat; "
                "the detected shock and downstream post-shock region are masked because the "
                "geometric-throat isentropic area-Mach relation is not applicable across entropy production"
            )
        else:
            note = (
                "subsonic branch before the throat and supersonic branch after the throat; "
                "no sharp shock was detected, so only local non-isentropic jumps would be excluded"
            )
    else:
        theory[x > throat_x] = supersonic_branch[x > throat_x]
        note = "subsonic branch before the throat and supersonic branch after the throat"

    return theory, valid, note, shock_x, shock_mask


def rms_error(cfd: np.ndarray, theory: np.ndarray, valid: np.ndarray) -> float:
    if not np.any(valid):
        return float("nan")
    return float(np.sqrt(np.mean((cfd[valid] - theory[valid]) ** 2)))


def validate_area_mach(
    centerline_csv: Path,
    block_mesh_dict: Path,
    case_name: str,
    images_dir: Path,
    gamma: float = GAMMA,
    throat_x: float | None = None,
) -> dict[str, object]:
    data = np.genfromtxt(centerline_csv, delimiter=",", names=True)
    x = np.asarray(data["x"])
    mach = np.asarray(data["Mach"])

    geom_x, geom_area = nozzle_profile(block_mesh_dict)
    throat_i = int(np.argmin(geom_area))
    throat_x = float(geom_x[throat_i]) if throat_x is None else throat_x
    throat_area = float(np.min(geom_area))
    area = interpolate_area(x, geom_x, geom_area)
    area_ratio = area / throat_area

    subsonic = solve_branch(area_ratio, False, gamma)
    supersonic = solve_branch(area_ratio, True, gamma)
    theory, valid, note, shock_x, shock_mask = branch_for_case(
        case_name,
        x,
        area_ratio,
        subsonic,
        supersonic,
        throat_x,
        mach,
    )
    error = rms_error(mach, theory, valid)
    pre_shock_error = float("nan")
    post_shock_error = float("nan")
    post_shock_points = 0

    if case_name == "internal_shock" and shock_x is not None:
        pre_valid = valid & (x < shock_x)
        pre_shock_error = rms_error(mach, theory, pre_valid)

        post_valid = (x > shock_x) & ~shock_mask & (mach < 0.95)
        post_shock_points = int(np.count_nonzero(post_valid))
        if post_shock_points >= 3:
            effective_a_star = np.median(area[post_valid] / area_mach(mach[post_valid], gamma))
            post_area_ratio = area / effective_a_star
            post_area_ratio = np.maximum(post_area_ratio, 1.0)
            post_theory = solve_branch(post_area_ratio, False, gamma)
            post_shock_error = rms_error(mach, post_theory, post_valid)
        else:
            post_theory = None
    else:
        post_theory = None

    images_dir.mkdir(parents=True, exist_ok=True)
    area_plot = images_dir / f"{case_name}_area_ratio.png"
    mach_plot = images_dir / f"{case_name}_mach_area_relation.png"

    plt.figure(figsize=(8, 4.5))
    plt.plot(x, area_ratio, linewidth=2)
    plt.axvline(throat_x, color="black", linestyle="--", linewidth=1, label="throat")
    plt.xlabel("x [m]")
    plt.ylabel("A(x) / A* [-]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(area_plot, dpi=200)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    plt.plot(x, mach, label="CFD centerline", linewidth=2)
    plt.plot(x, subsonic, "--", label="area-Mach subsonic branch", linewidth=1.8)
    plt.plot(x, supersonic, "--", label="area-Mach supersonic branch", linewidth=1.8)
    plt.plot(x[valid], theory[valid], color="black", linewidth=1.5, label="selected valid comparison")
    if post_theory is not None and post_shock_points >= 3:
        post_valid = (x > shock_x) & ~shock_mask & (mach < 0.95)
        plt.plot(
            x[post_valid],
            post_theory[post_valid],
            color="tab:green",
            linewidth=1.5,
            label="post-shock subsonic isentropic fit",
        )
    if np.any(~valid):
        plt.scatter(x[~valid], mach[~valid], s=10, color="tab:red", label="masked non-isentropic region")
    if shock_x is not None:
        plt.axvline(shock_x, color="tab:red", linestyle=":", linewidth=1.5, label="detected shock")
    plt.axvline(throat_x, color="0.2", linestyle="--", linewidth=1, label="throat")
    plt.xlabel("x [m]")
    plt.ylabel("Mach number [-]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(mach_plot, dpi=200)
    plt.close()

    return {
        "rms_error": error,
        "pre_shock_rms_error": pre_shock_error,
        "post_shock_rms_error": post_shock_error,
        "post_shock_points": post_shock_points,
        "valid_points": int(np.count_nonzero(valid)),
        "total_points": int(len(valid)),
        "throat_x": throat_x,
        "throat_area": throat_area,
        "area_ratio_min": float(np.min(area_ratio)),
        "area_ratio_max": float(np.max(area_ratio)),
        "shock_x": shock_x,
        "note": note,
        "mach_plot": mach_plot,
        "area_plot": area_plot,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--centerline", type=Path, required=True)
    parser.add_argument("--block-mesh-dict", type=Path, required=True)
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--images-dir", type=Path, default=Path("docs/images"))
    parser.add_argument("--gamma", type=float, default=GAMMA)
    parser.add_argument("--throat-x", type=float)
    args = parser.parse_args()

    result = validate_area_mach(
        args.centerline,
        args.block_mesh_dict,
        args.case_name,
        args.images_dir,
        args.gamma,
        args.throat_x,
    )
    print(f"area-Mach RMS error = {result['rms_error']:.6g}")
    print(f"valid comparison points = {result['valid_points']} / {result['total_points']}")
    print(f"Mach plot: {result['mach_plot']}")
    print(f"Area-ratio plot: {result['area_plot']}")


if __name__ == "__main__":
    main()

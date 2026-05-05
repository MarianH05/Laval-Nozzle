#!/usr/bin/env python3
"""Collect and plot mesh-independence results for choked Laval nozzle cases."""

from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import numpy as np

from postprocess_centerline import latest_time, write_centerline
from validate_case import (
    choking_check,
    identify_flow_patches,
    mass_flow_assessment,
    mesh_cell_count,
    parse_boundary,
    parse_check_mesh,
    patch_mass_flow,
)


VARIANTS = [
    ("coarse", Path("cases/mesh_study/coarse"), 20000),
    ("medium", Path("cases/mesh_study/medium"), 70000),
    ("fine", Path("cases/mesh_study/fine"), 150000),
]


def fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return ""
    if number == 0:
        return "0"
    if abs(number) >= 1e6 or abs(number) < 1e-3:
        return f"{number:.6e}"
    return f"{number:.6g}"


def parse_runtime(log_path: Path) -> float | None:
    if not log_path.exists():
        return None
    matches = re.findall(r"ExecutionTime\s*=\s*([-+0-9.eE]+)\s+s", log_path.read_text(errors="ignore"))
    return float(matches[-1]) if matches else None


def expected_cells(block_mesh_dict: Path) -> int | None:
    if not block_mesh_dict.exists():
        return None
    total = 0
    text = block_mesh_dict.read_text()
    for nx, ny, nz in re.findall(r"\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)\s+simpleGrading", text):
        total += int(nx) * int(ny) * int(nz)
    return total or None


def collect_case(name: str, case_dir: Path, target_cells: int) -> dict[str, object]:
    row: dict[str, object] = {
        "mesh": name,
        "case_dir": str(case_dir),
        "target_cells": target_cells,
        "total_cell_count": expected_cells(case_dir / "system/blockMeshDict"),
        "max_non_orthogonality": None,
        "max_skewness": None,
        "mdot_in": None,
        "mdot_out": None,
        "mass_error_percent": None,
        "mass_assessment": "",
        "throat_Mach": None,
        "max_Mach": None,
        "runtime_s": parse_runtime(case_dir / "log.rhoCentralFoam"),
        "status": "not run",
    }

    mesh_ready = (case_dir / "constant/polyMesh/owner").exists()
    if mesh_ready:
        row["total_cell_count"] = mesh_cell_count(case_dir)
        mesh = parse_check_mesh(case_dir / "log.checkMesh")
        if mesh.get("available"):
            row["max_non_orthogonality"] = mesh.get("max_non_orthogonality")
            row["max_skewness"] = mesh.get("max_skewness")
    else:
        return row

    try:
        time_dir = latest_time(case_dir)
    except FileNotFoundError:
        return row

    required_fields = [time_dir / field for field in ("rho", "U", "p", "T")]
    if not mesh_ready or not all(path.exists() for path in required_fields):
        row["status"] = "missing mesh or latest fields"
        return row

    patches = parse_boundary(case_dir / "constant/polyMesh/boundary")
    inlet, outlet = identify_flow_patches(patches, None, None)
    mdot_in = patch_mass_flow(case_dir, time_dir, inlet)
    mdot_out = patch_mass_flow(case_dir, time_dir, outlet)
    mass_error = abs(abs(mdot_in) - abs(mdot_out)) / max(abs(mdot_in), abs(mdot_out), 1e-300) * 100.0

    centerline_csv = case_dir / "postProcessing/centerline/centerline_latest.csv"
    write_centerline(case_dir, time_dir.name, centerline_csv, bins=500)
    choking = choking_check(centerline_csv, 0.05, None)

    row.update({
        "mdot_in": mdot_in,
        "mdot_out": mdot_out,
        "mass_error_percent": mass_error,
        "mass_assessment": mass_flow_assessment(mass_error),
        "throat_Mach": choking["throat_mach"],
        "max_Mach": choking["max_mach"],
        "status": "computed",
    })
    return row


def write_markdown(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "mesh",
        "case_dir",
        "target_cells",
        "total_cell_count",
        "max_non_orthogonality",
        "max_skewness",
        "mdot_in",
        "mdot_out",
        "mass_error_percent",
        "mass_assessment",
        "throat_Mach",
        "max_Mach",
        "runtime_s",
        "status",
    ]
    with path.open("w") as f:
        f.write("# Mesh Independence Study\n\n")
        f.write("All variants use the choked Laval nozzle physics, geometry, solver, and runtime controls. Only `system/blockMeshDict` resolution changes.\n\n")
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(fmt(row.get(column)) for column in columns) + " |\n")

        f.write("\n## Commands\n\n")
        for name, case_dir, _ in VARIANTS:
            f.write(f"- `{name}`: `./Allrun {case_dir}`\n")
        f.write("- After one or more cases finish: `python3 scripts/mesh_independence.py`\n\n")

        f.write("## Interpretation\n\n")
        computed = [row for row in rows if row["status"] == "computed"]
        if len(computed) >= 2:
            f.write(
                "Compare the change in throat Mach and mass-flow error as cell count increases. "
                "For portfolio purposes, the medium mesh is sufficient if its throat Mach and mass flow "
                "are close to the fine mesh while keeping runtime materially lower.\n"
            )
        else:
            f.write(
                "The cases have not all been solved yet, so sufficiency cannot be concluded from computed results. "
                "The medium mesh is the intended portfolio default because it matches the existing 70000-cell baseline; "
                "confirm it by running at least the medium and fine cases and checking that throat Mach and mass flow change only slightly.\n"
            )


def plot_metric(rows: list[dict[str, object]], x_key: str, y_key: str, output: Path, ylabel: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    xs = []
    ys = []
    labels = []
    for row in rows:
        x = row.get(x_key)
        y = row.get(y_key)
        if x is not None and y is not None:
            xs.append(float(x))
            ys.append(float(y))
            labels.append(str(row["mesh"]))

    plt.figure(figsize=(7, 4.5))
    if xs:
        order = np.argsort(xs)
        xs_arr = np.array(xs)[order]
        ys_arr = np.array(ys)[order]
        labels_arr = np.array(labels)[order]
        plt.plot(xs_arr, ys_arr, marker="o", linewidth=2)
        for x, y, label in zip(xs_arr, ys_arr, labels_arr):
            plt.annotate(label, (x, y), textcoords="offset points", xytext=(4, 5))
        plt.xlabel("Cell count")
        plt.ylabel(ylabel)
    else:
        plt.text(0.5, 0.5, "No computed mesh-study data yet", ha="center", va="center")
        plt.xticks([])
        plt.yticks([])
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/mesh_independence.md"))
    parser.add_argument("--images-dir", type=Path, default=Path("docs/images"))
    args = parser.parse_args()

    rows = [collect_case(name, case_dir, target) for name, case_dir, target in VARIANTS]
    write_markdown(rows, args.output)
    plot_metric(rows, "total_cell_count", "throat_Mach", args.images_dir / "mesh_independence_throat_mach.png", "Throat Mach number")
    plot_metric(rows, "total_cell_count", "mdot_out", args.images_dir / "mesh_independence_mass_flow.png", "Outlet mass flow rate [kg/s]")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.images_dir / 'mesh_independence_throat_mach.png'}")
    print(f"Wrote {args.images_dir / 'mesh_independence_mass_flow.png'}")


if __name__ == "__main__":
    main()

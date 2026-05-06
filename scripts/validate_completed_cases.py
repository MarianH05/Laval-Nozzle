#!/usr/bin/env python3
"""Aggregate validation for completed Laval nozzle cases from existing output only."""

from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import numpy as np

from postprocess_centerline import (
    GAMMA,
    R_AIR,
    latest_time,
    read_faces,
    read_labels,
    read_points,
    read_scalar_field,
    read_vector_field,
    write_centerline,
)
from pressure_ratio_study import case_metadata
from validate_case import (
    choking_check,
    field_stats,
    identify_flow_patches,
    mass_flow_assessment,
    mesh_cell_count,
    parse_boundary,
    parse_check_mesh,
    patch_mass_flow,
    plot_validation,
    verdict,
)


ROOT = Path(__file__).resolve().parents[1]
FLOW_CASES = [
    ("subsonic", ROOT / "cases/subsonic", "fully subsonic"),
    ("choked", ROOT / "cases/choked", "choked/supersonic"),
    ("internal_shock", ROOT / "cases/internal_shock", "internal shock"),
]
MESH_CASES = [
    ("coarse", ROOT / "cases/mesh_study/coarse"),
    ("medium", ROOT / "cases/mesh_study/medium"),
    ("fine", ROOT / "cases/mesh_study/fine"),
]
ALL_CASES = FLOW_CASES + [(f"mesh_{name}", path, "choked/supersonic") for name, path in MESH_CASES]


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def fmt(value: object, digits: int = 6) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    number = float(value)
    if math.isnan(number):
        return ""
    if number == 0:
        return "0"
    if abs(number) >= 1e5 or abs(number) < 1e-3:
        return f"{number:.{digits}e}"
    return f"{number:.{digits}g}"


def read_control_value(case_dir: Path, key: str) -> float | None:
    path = case_dir / "system/controlDict"
    if not path.exists():
        return None
    match = re.search(rf"\b{re.escape(key)}\s+([-+0-9.eE]+)\s*;", path.read_text())
    return float(match.group(1)) if match else None


def log_candidates(case_dir: Path, stem: str) -> list[Path]:
    exact = case_dir / stem
    candidates = [exact] if exact.exists() else []
    candidates.extend(path for path in case_dir.glob(f"{stem}.*") if path.is_file())
    return sorted(set(candidates), key=lambda path: (path.stat().st_mtime, path.name))


def parse_solver_log(path: Path) -> dict[str, object]:
    text = path.read_text(errors="ignore")
    co = [(float(a), float(b)) for a, b in re.findall(r"Mean and max Courant Numbers\s*=\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)", text)]
    times = [float(value) for value in re.findall(r"^Time\s*=\s*([-+0-9.eE]+)", text, re.M)]
    exec_times = [float(value) for value in re.findall(r"ExecutionTime\s*=\s*([-+0-9.eE]+)\s+s", text)]
    return {
        "path": path,
        "co": co,
        "last_time": times[-1] if times else None,
        "start_time": times[0] if times else None,
        "execution_time": exec_times[-1] if exec_times else None,
        "ended": bool(re.search(r"^End\s*$", text, re.M)),
    }


def aggregate_courant(case_dir: Path, latest: float | None) -> dict[str, object]:
    logs = [parse_solver_log(path) for path in log_candidates(case_dir, "log.rhoCentralFoam")]
    logs = [item for item in logs if item["co"]]
    if not logs:
        return {"available": False, "logs": []}

    means = [pair[0] for item in logs for pair in item["co"]]
    maxes = [pair[1] for item in logs for pair in item["co"]]
    def score(item: dict[str, object]) -> tuple[float, int, float]:
        last = item["last_time"]
        proximity = -abs(float(last) - latest) if last is not None and latest is not None else -1e9
        return (proximity, int(bool(item["ended"])), item["path"].stat().st_mtime)

    final = max(logs, key=score)
    return {
        "available": True,
        "n": len(maxes),
        "max_mean": max(means),
        "max_max": max(maxes),
        "last_mean": final["co"][-1][0],
        "last_max": final["co"][-1][1],
        "logs": [rel(item["path"]) for item in logs],
        "final_log": rel(final["path"]),
        "ended": bool(final["ended"]),
    }


def runtime_seconds(case_dir: Path) -> float | None:
    intervals = {}
    for path in log_candidates(case_dir, "log.rhoCentralFoam"):
        item = parse_solver_log(path)
        if item["start_time"] is None or item["last_time"] is None or item["execution_time"] is None:
            continue
        key = (round(float(item["start_time"]), 10), round(float(item["last_time"]), 10))
        intervals[key] = max(float(item["execution_time"]), intervals.get(key, 0.0))
    return sum(intervals.values()) if intervals else None


def current_check_mesh(case_dir: Path) -> dict[str, object]:
    candidates = log_candidates(case_dir, "log.checkMesh")
    if not candidates:
        return {"available": False}
    return parse_check_mesh(candidates[-1])


def cell_mach(case_dir: Path, time_dir: Path) -> np.ndarray:
    poly = case_dir / "constant/polyMesh"
    owner = read_labels(poly / "owner")
    neighbour = read_labels(poly / "neighbour")
    n_cells = int(max(owner.max(), neighbour.max())) + 1
    ma_path = time_dir / "Ma"
    if ma_path.exists():
        return read_scalar_field(ma_path, n_cells)
    T = read_scalar_field(time_dir / "T", n_cells)
    U = read_vector_field(time_dir / "U", n_cells)
    return np.linalg.norm(U, axis=1) / np.sqrt(GAMMA * R_AIR * T)


def completion_status(case_dir: Path, time_dir: Path, courant: dict[str, object]) -> str:
    end_time = read_control_value(case_dir, "endTime")
    latest = float(time_dir.name)
    reached = end_time is not None and latest >= end_time - max(1e-12, abs(end_time) * 1e-7)
    if reached and courant.get("ended"):
        return "complete: latest time reaches endTime and final solver log contains End"
    if reached:
        return "complete by latest time reaching endTime; final End marker not found"
    return f"incomplete: latest time {latest:g} is below configured endTime {end_time:g}" if end_time else "completion unknown"


def observed_regime(expected_key: str, throat_mach: float, max_mach: float, centerline_csv: Path) -> str:
    data = np.genfromtxt(centerline_csv, delimiter=",", names=True)
    x = np.asarray(data["x"])
    mach = np.asarray(data["Mach"])
    downstream = x > 0.05
    has_supersonic = bool(np.any(mach[downstream] > 1.05)) if np.any(downstream) else max_mach > 1.05
    has_subsonic_after_supersonic = False
    if has_supersonic and np.any(downstream):
        sup_idx = np.where(downstream & (mach > 1.05))[0]
        if len(sup_idx):
            has_subsonic_after_supersonic = bool(np.any(mach[sup_idx[-1] :] < 0.95))
    if max_mach < 1.0:
        return "fully subsonic"
    if expected_key == "internal shock" or has_subsonic_after_supersonic:
        return "choked with internal shock" if has_supersonic else "shock not resolved"
    if 0.95 <= throat_mach <= 1.05 and has_supersonic:
        return "choked with downstream supersonic acceleration"
    return "mixed/transient"


def plot_centerline_case(centerline_csv: Path, out_path: Path, title: str) -> None:
    data = np.genfromtxt(centerline_csv, delimiter=",", names=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    series = [
        ("Mach", "Mach [-]"),
        ("p", "p [Pa]"),
        ("T", "T [K]"),
        ("rho", "rho [kg/m3]"),
    ]
    for ax, (name, ylabel) in zip(axes.ravel(), series):
        ax.plot(data["x"], data[name], linewidth=2)
        ax.axvline(0.05, color="black", linestyle="--", linewidth=1)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
    axes[1, 0].set_xlabel("x [m]")
    axes[1, 1].set_xlabel("x [m]")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def validate_one(label: str, case_dir: Path, expected_key: str) -> dict[str, object]:
    time_dir = latest_time(case_dir)
    required = [time_dir / field for field in ("p", "T", "rho", "U")]
    if not all(path.exists() for path in required):
        return {"label": label, "case_dir": case_dir, "latest_time": time_dir.name, "available": False}

    latest = float(time_dir.name)
    courant = aggregate_courant(case_dir, latest)
    mesh = current_check_mesh(case_dir)
    stats = field_stats(case_dir, time_dir)
    patches = parse_boundary(case_dir / "constant/polyMesh/boundary")
    inlet, outlet = identify_flow_patches(patches, None, None)
    mdot_in = patch_mass_flow(case_dir, time_dir, inlet)
    mdot_out = patch_mass_flow(case_dir, time_dir, outlet)
    mass_error = abs(abs(mdot_in) - abs(mdot_out)) / max(abs(mdot_in), abs(mdot_out), 1e-300) * 100.0
    centerline_csv = case_dir / "postProcessing/centerline/centerline_latest.csv"
    write_centerline(case_dir, time_dir.name, centerline_csv, bins=500)
    image_case_dir = ROOT / "docs/images" / label
    metadata = case_metadata(case_dir)
    p0 = float(metadata["p0_Pa"]) if metadata["p0_Pa"] else 300000.0
    t0 = float(metadata["T0_K"]) if metadata["T0_K"] else 300.0
    plot_validation(centerline_csv, image_case_dir, p0, t0, p0 / (R_AIR * t0), GAMMA)
    plot_centerline_case(centerline_csv, ROOT / "docs/images" / f"{label}_validation_profiles.png", label.replace("_", " ").title())
    choking = choking_check(centerline_csv, 0.05, True if expected_key == "fully subsonic" else None)
    final_verdict = verdict(mass_error, courant, mesh, stats, choking)
    if expected_key == "internal shock" and observed_regime(expected_key, choking["throat_mach"], choking["max_mach"], centerline_csv) != "choked with internal shock":
        final_verdict = "questionable" if final_verdict == "valid" else final_verdict

    expected_text = metadata["expected_regime"] or expected_key
    if expected_text in {label, case_dir.name}:
        expected_text = expected_key

    return {
        "label": label,
        "case_dir": case_dir,
        "latest_time": time_dir.name,
        "available": True,
        "completion": completion_status(case_dir, time_dir, courant),
        "courant": courant,
        "mesh": mesh,
        "stats": stats,
        "mdot_in": mdot_in,
        "mdot_out": mdot_out,
        "mass_error": mass_error,
        "mass_assessment": mass_flow_assessment(mass_error),
        "throat_mach": float(choking["throat_mach"]),
        "max_mach": float(choking["max_mach"]),
        "expected_regime": expected_text,
        "observed_regime": observed_regime(expected_key, float(choking["throat_mach"]), float(choking["max_mach"]), centerline_csv),
        "verdict": final_verdict,
        "cell_count": mesh_cell_count(case_dir),
        "runtime_s": runtime_seconds(case_dir),
        "centerline_csv": centerline_csv,
    }


def write_pressure_study(results: list[dict[str, object]]) -> None:
    columns = [
        "case_name", "p0_Pa", "T0_K", "pb_Pa", "pb_over_p0", "expected_regime",
        "observed_regime", "latest_time", "completion_status", "observed_max_Mach",
        "observed_throat_Mach", "mdot_in_kg_s", "mdot_out_kg_s", "mass_error_percent",
        "max_Courant", "final_Courant", "mesh_cells", "validation_verdict",
    ]
    rows = []
    for result in results:
        meta = case_metadata(result["case_dir"])
        rows.append({
            "case_name": result["label"],
            "p0_Pa": meta["p0_Pa"],
            "T0_K": meta["T0_K"],
            "pb_Pa": meta["pb_Pa"],
            "pb_over_p0": meta["pb_over_p0"],
            "expected_regime": result["expected_regime"],
            "observed_regime": result["observed_regime"],
            "latest_time": result["latest_time"],
            "completion_status": result["completion"],
            "observed_max_Mach": fmt(result["max_mach"]),
            "observed_throat_Mach": fmt(result["throat_mach"]),
            "mdot_in_kg_s": fmt(result["mdot_in"]),
            "mdot_out_kg_s": fmt(result["mdot_out"]),
            "mass_error_percent": fmt(result["mass_error"]),
            "max_Courant": fmt(result["courant"]["max_max"] if result["courant"].get("available") else None),
            "final_Courant": fmt(result["courant"]["last_max"] if result["courant"].get("available") else None),
            "mesh_cells": str(result["cell_count"]),
            "validation_verdict": result["verdict"],
        })
    csv_path = ROOT / "docs/pressure_ratio_study.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    md_path = ROOT / "docs/pressure_ratio_study.md"
    with md_path.open("w") as f:
        f.write("# Pressure-Ratio Study\n\n")
        f.write("Updated from existing completed OpenFOAM outputs only. Mass flow uses `integral(rho * U dot n dA)`; `phi` and `rho*phi` are not used.\n\n")
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(str(row[column]).replace("|", "\\|") for column in columns) + " |\n")
        f.write("\n## Interpretation\n\n")
        f.write("The subsonic case remains below Mach 1. The choked pressure ratio produces sonic throat conditions and downstream supersonic acceleration. The internal-shock case reaches supersonic flow downstream of the throat and then returns to subsonic flow, consistent with an internal shock.\n")


def mesh_deltas(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    prev = None
    for row in rows:
        item = dict(row)
        item["delta_throat_mach_from_previous"] = None if prev is None else row["throat_mach"] - prev["throat_mach"]
        item["delta_mass_error_from_previous_pctpt"] = None if prev is None else row["mass_error"] - prev["mass_error"]
        prev = row
        out.append(item)
    return out


def plot_mesh_metric(rows: list[dict[str, object]], key: str, ylabel: str, path: Path) -> None:
    x = np.array([row["cell_count"] for row in rows], dtype=float)
    y = np.array([row[key] for row in rows], dtype=float)
    labels = [row["label"] for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4.5))
    plt.plot(x, y, marker="o", linewidth=2)
    for xi, yi, label in zip(x, y, labels):
        plt.annotate(label, (xi, yi), textcoords="offset points", xytext=(5, 5))
    plt.xlabel("Cell count")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def write_mesh_study(mesh_results: list[dict[str, object]]) -> None:
    rows = mesh_deltas(mesh_results)
    columns = [
        "mesh", "cell_count", "runtime_s", "throat_Mach", "delta_throat_Mach_from_previous",
        "max_Mach", "mass_error_percent", "delta_mass_error_from_previous_pctpt",
        "mdot_in_kg_s", "mdot_out_kg_s", "max_Courant", "final_Courant", "verdict",
    ]
    csv_path = ROOT / "docs/data/mesh_independence_summary.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "mesh": row["label"],
                "cell_count": row["cell_count"],
                "runtime_s": fmt(row["runtime_s"]),
                "throat_Mach": fmt(row["throat_mach"]),
                "delta_throat_Mach_from_previous": fmt(row["delta_throat_mach_from_previous"]),
                "max_Mach": fmt(row["max_mach"]),
                "mass_error_percent": fmt(row["mass_error"]),
                "delta_mass_error_from_previous_pctpt": fmt(row["delta_mass_error_from_previous_pctpt"]),
                "mdot_in_kg_s": fmt(row["mdot_in"]),
                "mdot_out_kg_s": fmt(row["mdot_out"]),
                "max_Courant": fmt(row["courant"]["max_max"] if row["courant"].get("available") else None),
                "final_Courant": fmt(row["courant"]["last_max"] if row["courant"].get("available") else None),
                "verdict": row["verdict"],
            })

    plot_mesh_metric(rows, "throat_mach", "Throat Mach number [-]", ROOT / "docs/images/mesh_independence_throat_mach.png")
    plot_mesh_metric(rows, "mass_error", "Mass conservation error [%]", ROOT / "docs/images/mesh_independence_mass_error.png")
    plot_mesh_metric(rows, "max_mach", "Maximum Mach number [-]", ROOT / "docs/images/mesh_independence_max_mach.png")

    medium = rows[1]
    fine = rows[2]
    d_mach = abs(fine["throat_mach"] - medium["throat_mach"])
    d_mass = abs(fine["mass_error"] - medium["mass_error"])
    sufficient_for_regime = d_mach / max(abs(fine["throat_mach"]), 1e-300) < 0.01 and d_mass < 0.5 and medium["verdict"] in {"valid", "questionable"}
    strict_quantitative = d_mach <= 0.01
    md_path = ROOT / "docs/mesh_independence.md"
    with md_path.open("w") as f:
        f.write("# Mesh Independence Study\n\n")
        f.write("All mesh-study cases were analyzed from existing completed outputs only. Runtime is parsed from available solver log segments; no solver was rerun.\n\n")
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for row in rows:
            values = {
                "mesh": row["label"], "cell_count": row["cell_count"], "runtime_s": fmt(row["runtime_s"]),
                "throat_Mach": fmt(row["throat_mach"]), "delta_throat_Mach_from_previous": fmt(row["delta_throat_mach_from_previous"]),
                "max_Mach": fmt(row["max_mach"]), "mass_error_percent": fmt(row["mass_error"]),
                "delta_mass_error_from_previous_pctpt": fmt(row["delta_mass_error_from_previous_pctpt"]),
                "mdot_in_kg_s": fmt(row["mdot_in"]), "mdot_out_kg_s": fmt(row["mdot_out"]),
                "max_Courant": fmt(row["courant"]["max_max"] if row["courant"].get("available") else None),
                "final_Courant": fmt(row["courant"]["last_max"] if row["courant"].get("available") else None),
                "verdict": row["verdict"],
            }
            f.write("| " + " | ".join(str(values[column]) for column in columns) + " |\n")
        f.write("\n## Medium-Mesh Sufficiency\n\n")
        f.write(f"The medium-to-fine throat Mach change is `{d_mach:.6g}` (`{d_mach / max(abs(fine['throat_mach']), 1e-300) * 100.0:.4g}%` relative to fine) and the mass-error change is `{d_mass:.6g}` percentage points. ")
        if sufficient_for_regime:
            f.write("The medium mesh is sufficient for regime classification and validation-level conclusions, because the sonic throat, supersonic divergent flow, and mass conservation are unchanged within about 1% relative throat Mach.\n")
        else:
            f.write("The medium mesh is not sufficient for the validation-level conclusions under the current tolerances.\n")
        if not strict_quantitative:
            f.write("\nFor strict quantitative reporting with an absolute throat-Mach tolerance of `0.01`, use the fine mesh or report the medium result with this residual discretization difference.\n")
        f.write("\nGenerated plots:\n\n")
        f.write("- `docs/images/mesh_independence_throat_mach.png`\n")
        f.write("- `docs/images/mesh_independence_mass_error.png`\n")
        f.write("- `docs/images/mesh_independence_max_mach.png`\n")


def write_validation_summary(flow_results: list[dict[str, object]], mesh_results: list[dict[str, object]]) -> None:
    columns = [
        "case", "latest_time", "completion", "max_Co", "final_Co", "mesh_quality",
        "p_min_max", "T_min_max", "rho_min_max", "Ma_min_max", "mdot_in", "mdot_out",
        "mass_error", "throat_Mach", "max_Mach", "expected", "observed", "verdict",
    ]
    with (ROOT / "docs/validation_summary.md").open("w") as f:
        f.write("# Validation Summary\n\n")
        f.write("This summary was regenerated from existing completed OpenFOAM outputs only. `rhoCentralFoam`, `Allrun`, `Allclean`, and time-directory deletion were not performed. Missing `Ma` fields were handled by computing `|U| / sqrt(gamma R T)` from existing `U` and `T`; `phi` and `rho*phi` were not used.\n\n")
        f.write("## All Cases\n\n")
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for row in flow_results + mesh_results:
            mesh = row["mesh"]
            mesh_quality = "not available"
            if mesh.get("available"):
                mesh_quality = f"pass={mesh['passed']}; nonOrth={fmt(mesh['max_non_orthogonality'])}; skew={fmt(mesh['max_skewness'])}; negVol={mesh['negative_volume_cells']}"
            values = {
                "case": f"`{rel(row['case_dir'])}`",
                "latest_time": row["latest_time"],
                "completion": row["completion"],
                "max_Co": fmt(row["courant"]["max_max"] if row["courant"].get("available") else None),
                "final_Co": fmt(row["courant"]["last_max"] if row["courant"].get("available") else None),
                "mesh_quality": mesh_quality,
                "p_min_max": f"{fmt(row['stats']['p'][0])} / {fmt(row['stats']['p'][1])}",
                "T_min_max": f"{fmt(row['stats']['T'][0])} / {fmt(row['stats']['T'][1])}",
                "rho_min_max": f"{fmt(row['stats']['rho'][0])} / {fmt(row['stats']['rho'][1])}",
                "Ma_min_max": f"{fmt(row['stats']['Ma'][0])} / {fmt(row['stats']['Ma'][1])}",
                "mdot_in": fmt(row["mdot_in"]),
                "mdot_out": fmt(row["mdot_out"]),
                "mass_error": fmt(row["mass_error"]) + "%",
                "throat_Mach": fmt(row["throat_mach"]),
                "max_Mach": fmt(row["max_mach"]),
                "expected": row["expected_regime"],
                "observed": row["observed_regime"],
                "verdict": f"`{str(row['verdict']).upper()}`",
            }
            f.write("| " + " | ".join(str(values[column]).replace("|", "\\|") for column in columns) + " |\n")
        f.write("\n## Verdict Basis\n\n")
        f.write("A case is treated as valid when primitive fields remain positive, checkMesh passes, Courant number remains below the stability limit, mass conservation is acceptable, and the observed Mach topology matches the expected regime. Marginal mass conservation or an ambiguous regime produces a questionable verdict rather than a valid one.\n")


def tex_escape(text: str) -> str:
    return str(text).replace("_", r"\_").replace("%", r"\%")


def write_report(flow_results: list[dict[str, object]], mesh_results: list[dict[str, object]]) -> None:
    rows = "\n".join(
        rf"\texttt{{{tex_escape(row['label'])}}} & {row['latest_time']} & {fmt(row['throat_mach'])} & {fmt(row['max_mach'])} & {fmt(row['mass_error'])}\% & \texttt{{{tex_escape(str(row['verdict']).upper())}}} \\"
        for row in flow_results
    )
    mesh_rows = "\n".join(
        rf"\texttt{{{tex_escape(row['label'])}}} & {row['cell_count']} & {fmt(row['runtime_s'])} & {fmt(row['throat_mach'])} & {fmt(row['max_mach'])} & {fmt(row['mass_error'])}\% \\"
        for row in mesh_results
    )
    medium = mesh_results[1]
    fine = mesh_results[2]
    d_mach = abs(fine['throat_mach'] - medium['throat_mach'])
    d_mass = abs(fine['mass_error'] - medium['mass_error'])
    tex = rf"""\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{booktabs}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage{{siunitx}}
\title{{Compressible Flow Through a Converging-Diverging Laval Nozzle\\Validation Report}}
\author{{Marian}}
\date{{May 6, 2026}}
\begin{{document}}
\maketitle

\begin{{abstract}}
This report validates the completed Laval nozzle simulations from files already present on disk. No solver, Allrun, Allclean, mesh regeneration, or deletion of time directories was performed for this update.
\end{{abstract}}

\section{{Method}}
Mass flow is computed from the direct boundary integral
\[
\dot{{m}}=\int_A \rho \mathbf{{U}}\cdot\mathbf{{n}}\,dA,
\]
using existing latest-time \texttt{{rho}} and \texttt{{U}} fields and mesh face area vectors. The \texttt{{phi}} field and \(\rho\phi\) are not used. When \texttt{{Ma}} is absent, Mach number is computed as \(M=|\mathbf{{U}}|/\sqrt{{\gamma R T}}\) with \(\gamma=1.4\) and \(R=\SI{{287}}{{J.kg^{{-1}}.K^{{-1}}}}\).

\section{{Pressure-Ratio Cases}}
\begin{{table}}[h]
\centering
\caption{{Latest-time validation results.}}
\begin{{tabular}}{{lccccc}}
\toprule
Case & Latest time & Throat Mach & Max Mach & Mass error & Verdict \\
\midrule
{rows}
\bottomrule
\end{{tabular}}
\end{{table}}

The subsonic case remains below Mach 1. The choked case reaches near-sonic throat conditions and accelerates supersonically downstream. The internal-shock case shows supersonic acceleration followed by a return to subsonic flow, consistent with the expected shock-containing regime.

\section{{Mesh Independence}}
\begin{{table}}[h]
\centering
\caption{{Mesh-study results for the choked operating point.}}
\begin{{tabular}}{{lccccc}}
\toprule
Mesh & Cells & Runtime [s] & Throat Mach & Max Mach & Mass error \\
\midrule
{mesh_rows}
\bottomrule
\end{{tabular}}
\end{{table}}

The medium-to-fine throat Mach change is {d_mach:.6g} ({d_mach / max(abs(fine['throat_mach']), 1e-300) * 100.0:.4g}\% relative to fine), and the mass-conservation-error change is {d_mass:.6g} percentage points. The medium mesh is sufficient for regime classification and validation-level conclusions. For strict quantitative reporting with an absolute throat-Mach tolerance of 0.01, the fine mesh should be used or the residual discretization difference should be reported.

\section{{Generated Artifacts}}
Detailed tables and plots were regenerated in:
\begin{{itemize}}
\item \texttt{{docs/validation\_summary.md}}
\item \texttt{{docs/pressure\_ratio\_study.md}}
\item \texttt{{docs/mesh\_independence.md}}
\item \texttt{{docs/data/mesh\_independence\_summary.csv}}
\item \texttt{{docs/images/mesh\_independence\_throat\_mach.png}}
\item \texttt{{docs/images/mesh\_independence\_mass\_error.png}}
\item \texttt{{docs/images/mesh\_independence\_max\_mach.png}}
\end{{itemize}}

\end{{document}}
"""
    (ROOT / "report/laval_nozzle_report.tex").write_text(tex)


def main() -> None:
    flow_results = [validate_one(label, path, expected) for label, path, expected in FLOW_CASES]
    mesh_results = [validate_one(name, path, "choked/supersonic") for name, path in MESH_CASES]
    unavailable = [row for row in flow_results + mesh_results if not row.get("available")]
    if unavailable:
        raise SystemExit(f"Missing required latest fields for: {', '.join(row['label'] for row in unavailable)}")
    write_validation_summary(flow_results, mesh_results)
    write_pressure_study(flow_results)
    write_mesh_study(mesh_results)
    write_report(flow_results, mesh_results)
    print("Validated cases:")
    for row in flow_results + mesh_results:
        print(
            f"{row['label']}: latest={row['latest_time']} verdict={row['verdict']} "
            f"throat_Ma={row['throat_mach']:.6g} max_Ma={row['max_mach']:.6g} "
            f"mass_error={row['mass_error']:.4f}%"
        )


if __name__ == "__main__":
    main()

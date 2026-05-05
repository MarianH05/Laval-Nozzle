#!/usr/bin/env python3
"""Validate a rhoCentralFoam Laval nozzle case without requiring phi on disk."""

from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import numpy as np

from area_mach_validation import validate_area_mach
from plot_time_history import analyze_time_history
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
from pressure_ratio_study import case_metadata, format_number, upsert_row, write_markdown


def parse_boundary(path: Path) -> dict[str, dict[str, int | str]]:
    text = path.read_text()
    patches: dict[str, dict[str, int | str]] = {}
    for match in re.finditer(r"\n\s*(\w+)\s*\{([^{}]*)\}", text, re.S):
        name, body = match.groups()
        patch_type = re.search(r"type\s+(\w+);", body)
        n_faces = re.search(r"nFaces\s+(\d+);", body)
        start_face = re.search(r"startFace\s+(\d+);", body)
        if patch_type and n_faces and start_face:
            patches[name] = {
                "type": patch_type.group(1),
                "nFaces": int(n_faces.group(1)),
                "startFace": int(start_face.group(1)),
            }
    return patches


def face_area_vector(vertices: np.ndarray) -> np.ndarray:
    area = np.zeros(3)
    for i in range(len(vertices)):
        area += np.cross(vertices[i], vertices[(i + 1) % len(vertices)])
    return 0.5 * area


def identify_flow_patches(patches: dict[str, dict[str, int | str]], inlet: str | None, outlet: str | None) -> tuple[str, str]:
    names = list(patches)
    inlet_name = inlet if inlet in patches else None
    outlet_name = outlet if outlet in patches else None

    if inlet_name is None:
        inlet_name = next((name for name in names if "inlet" in name.lower()), None)
    if outlet_name is None:
        outlet_name = next((name for name in names if "outlet" in name.lower()), None)

    if inlet_name is None or outlet_name is None:
        patch_list = format_patch_list(patches)
        raise KeyError(f"Could not identify inlet/outlet patches from boundary file. Available patches: {patch_list}")
    return inlet_name, outlet_name


def format_patch_list(patches: dict[str, dict[str, int | str]]) -> str:
    return ", ".join(f"{name}({values['type']})" for name, values in patches.items())


def patch_mass_flow(case_dir: Path, time_dir: Path, patch_name: str) -> float:
    """Compute integral rho * U dot n dA over a boundary patch using owner-cell values."""
    poly = case_dir / "constant/polyMesh"
    patches = parse_boundary(poly / "boundary")
    if patch_name not in patches:
        raise KeyError(f"Patch '{patch_name}' not found. Available patches: {', '.join(patches)}")

    faces = read_faces(poly / "faces")
    points = read_points(poly / "points")
    owner = read_labels(poly / "owner")
    neighbour = read_labels(poly / "neighbour")
    n_cells = int(max(owner.max(), neighbour.max())) + 1
    rho = read_scalar_field(time_dir / "rho", n_cells)
    U = read_vector_field(time_dir / "U", n_cells)

    patch = patches[patch_name]
    start = int(patch["startFace"])
    stop = start + int(patch["nFaces"])
    mdot = 0.0
    for face_i in range(start, stop):
        cell_i = owner[face_i]
        area_vec = face_area_vector(points[faces[face_i]])
        mdot += rho[cell_i] * float(np.dot(U[cell_i], area_vec))
    return mdot


def mass_flow_assessment(mass_error: float) -> str:
    if mass_error < 1.0:
        return "excellent"
    if mass_error < 3.0:
        return "acceptable"
    if mass_error > 5.0:
        return "problematic"
    return "marginal"


def parse_courant(log_path: Path) -> dict[str, float | int | bool]:
    if not log_path.exists():
        return {"available": False}
    means = []
    maxes = []
    for line in log_path.read_text(errors="ignore").splitlines():
        match = re.search(r"Mean and max Courant Numbers\s*=\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)", line)
        if match:
            means.append(float(match.group(1)))
            maxes.append(float(match.group(2)))
    if not maxes:
        return {"available": False}
    return {
        "available": True,
        "n": len(maxes),
        "max_mean": max(means),
        "max_max": max(maxes),
        "last_mean": means[-1],
        "last_max": maxes[-1],
    }


def parse_check_mesh(log_path: Path) -> dict[str, float | int | bool | None]:
    if not log_path.exists():
        return {"available": False}
    text = log_path.read_text(errors="ignore")
    non_orth = re.search(r"Mesh non-orthogonality Max:\s*([-+0-9.eE]+)", text)
    skew = re.search(r"Max skewness\s*=\s*([-+0-9.eE]+)", text)
    negative = re.search(r"Failed\s+(\d+)\s+cells with negative volume", text)
    return {
        "available": True,
        "max_non_orthogonality": float(non_orth.group(1)) if non_orth else None,
        "max_skewness": float(skew.group(1)) if skew else None,
        "negative_volume_cells": int(negative.group(1)) if negative else 0,
        "passed": "Mesh OK." in text,
    }


def mesh_cell_count(case_dir: Path) -> int:
    poly = case_dir / "constant/polyMesh"
    owner = read_labels(poly / "owner")
    neighbour = read_labels(poly / "neighbour")
    return int(max(owner.max(), neighbour.max())) + 1


def field_stats(case_dir: Path, time_dir: Path) -> dict[str, tuple[float, float]]:
    poly = case_dir / "constant/polyMesh"
    owner = read_labels(poly / "owner")
    neighbour = read_labels(poly / "neighbour")
    n_cells = int(max(owner.max(), neighbour.max())) + 1
    p = read_scalar_field(time_dir / "p", n_cells)
    T = read_scalar_field(time_dir / "T", n_cells)
    rho = read_scalar_field(time_dir / "rho", n_cells)
    U = read_vector_field(time_dir / "U", n_cells)
    ma_path = time_dir / "Ma"
    Ma = read_scalar_field(ma_path, n_cells) if ma_path.exists() else np.linalg.norm(U, axis=1) / np.sqrt(GAMMA * R_AIR * T)
    return {
        "p": (float(np.min(p)), float(np.max(p))),
        "T": (float(np.min(T)), float(np.max(T))),
        "rho": (float(np.min(rho)), float(np.max(rho))),
        "Ma": (float(np.min(Ma)), float(np.max(Ma))),
    }


def isentropic_from_mach(mach: np.ndarray, gamma: float) -> dict[str, np.ndarray]:
    t_ratio = 1.0 / (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    return {
        "T_T0": t_ratio,
        "p_p0": t_ratio ** (gamma / (gamma - 1.0)),
        "rho_rho0": t_ratio ** (1.0 / (gamma - 1.0)),
    }


def plot_validation(centerline_csv: Path, images_dir: Path, p0: float, T0: float, rho0: float, gamma: float) -> dict[str, float]:
    data = np.genfromtxt(centerline_csv, delimiter=",", names=True)
    x = data["x"]
    mach = data["Mach"]
    p_ratio = data["p"] / p0
    t_ratio = data["T"] / T0
    rho_ratio = data["rho"] / rho0
    theory = isentropic_from_mach(mach, gamma)

    images_dir.mkdir(parents=True, exist_ok=True)
    plots = [
        ("mach_vs_x.png", mach, mach, "Mach number [-]"),
        ("pressure_ratio_vs_x.png", p_ratio, theory["p_p0"], "p / p0 [-]"),
        ("temperature_ratio_vs_x.png", t_ratio, theory["T_T0"], "T / T0 [-]"),
        ("density_ratio_vs_x.png", rho_ratio, theory["rho_rho0"], "rho / rho0 [-]"),
    ]
    for filename, cfd, ref, ylabel in plots:
        plt.figure(figsize=(8, 4.5))
        plt.plot(x, cfd, label="CFD centerline", linewidth=2)
        if filename == "mach_vs_x.png":
            plt.plot(x, ref, "--", label="CFD Mach used for isentropic ratios", alpha=0.5)
        else:
            plt.plot(x, ref, "--", label="Isentropic from CFD Mach", linewidth=2)
        plt.xlabel("x [m]")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(images_dir / filename, dpi=200)
        plt.close()

    return {
        "p_rms_error": float(np.sqrt(np.mean((p_ratio - theory["p_p0"]) ** 2))),
        "T_rms_error": float(np.sqrt(np.mean((t_ratio - theory["T_T0"]) ** 2))),
        "rho_rms_error": float(np.sqrt(np.mean((rho_ratio - theory["rho_rho0"]) ** 2))),
    }


def choking_check(centerline_csv: Path, throat_x: float, subsonic_expected: bool | None) -> dict[str, float | str | bool]:
    data = np.genfromtxt(centerline_csv, delimiter=",", names=True)
    x = data["x"]
    mach = data["Mach"]
    region = np.abs(x - throat_x) <= 0.003
    if not np.any(region):
        region = np.abs(x - throat_x) == np.min(np.abs(x - throat_x))
    throat_mach = float(np.max(mach[region]))
    max_mach = float(np.max(mach))

    if subsonic_expected is True:
        status = "pass" if max_mach < 1.0 else "fail"
        message = "subsonic case: Mach should remain below 1"
    elif 0.95 <= throat_mach <= 1.05:
        status = "pass"
        message = "throat Mach is approximately sonic"
    elif max_mach < 0.95:
        status = "info"
        message = "flow appears subsonic; choking is not expected"
    else:
        status = "warn"
        message = "supersonic/choked case expected, but throat Mach is not near 1"
    return {"throat_mach": throat_mach, "max_mach": max_mach, "status": status, "message": message}


def verdict(mass_error: float, courant: dict, mesh: dict, stats: dict, choking: dict) -> str:
    invalid = False
    questionable = False
    if mass_error > 5.0:
        invalid = True
    elif mass_error > 3.0:
        questionable = True
    if courant.get("available") and float(courant["max_max"]) > 1.0:
        invalid = True
    if mesh.get("available") and (not mesh.get("passed") or int(mesh.get("negative_volume_cells", 0)) > 0):
        invalid = True
    if stats["p"][0] <= 0 or stats["T"][0] <= 0 or stats["rho"][0] <= 0:
        invalid = True
    if stats["Ma"][1] > 5.0:
        questionable = True
    if choking["status"] in {"fail", "warn"}:
        questionable = True
    return "invalid" if invalid else "questionable" if questionable else "valid"


def write_summary(path: Path, values: dict) -> None:
    def display_path(value: object) -> str:
        try:
            path_value = Path(value)
        except TypeError:
            return str(value)
        try:
            return str(path_value.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            return str(path_value)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("# Validation Summary\n\n")
        f.write(f"Case directory: `{display_path(values['case_dir'])}`\n\n")
        f.write(f"Latest time analyzed: `{values['time_name']}`\n\n")
        f.write("## Mass Flow Check\n\n")
        f.write("- method: direct patch integral `mdot = integral(rho * U dot n dA)`\n")
        f.write("- field source: OpenFOAM ASCII `rho` and `U` at the analyzed time; no `phi` or `rho*phi` required\n")
        f.write(f"- inlet patch: `{values['inlet_patch']}`\n")
        f.write(f"- outlet patch: `{values['outlet_patch']}`\n")
        f.write(f"- `mdot_in`: {values['mdot_in']:.8e} kg/s\n")
        f.write(f"- `mdot_out`: {values['mdot_out']:.8e} kg/s\n")
        f.write(f"- mass conservation error: {values['mass_error']:.4f}%\n")
        f.write(f"- assessment: {values['mass_assessment']}\n\n")
        f.write("Criteria: `<1%` excellent, `<3%` acceptable, `3-5%` marginal, `>5%` problematic.\n\n")

        f.write("## Courant Number Summary\n\n")
        c = values["courant"]
        if c.get("available"):
            f.write(f"- entries parsed: {c['n']}\n")
            f.write(f"- maximum mean Co: {c['max_mean']:.6g}\n")
            f.write(f"- maximum max Co: {c['max_max']:.6g}\n")
            f.write(f"- final mean/max Co: {c['last_mean']:.6g} / {c['last_max']:.6g}\n")
            f.write("- stability note: prefer `maxCo < 0.5`; warn if `maxCo > 1.0`\n\n")
        else:
            f.write("- solver log unavailable or no Courant entries found\n\n")

        f.write("## Mesh Quality Summary\n\n")
        m = values["mesh"]
        if m.get("available"):
            f.write(f"- maximum non-orthogonality: {m['max_non_orthogonality']}\n")
            f.write(f"- maximum skewness: {m['max_skewness']}\n")
            f.write(f"- negative volume cells: {m['negative_volume_cells']}\n")
            f.write(f"- mesh passed: {m['passed']}\n\n")
        else:
            f.write("- `log.checkMesh` unavailable\n\n")

        f.write("## Physical Sanity Checks\n\n")
        for field, (lo, hi) in values["stats"].items():
            f.write(f"- `{field}` min/max: {lo:.8g} / {hi:.8g}\n")
        f.write(f"- assessment: {values['sanity_assessment']}\n\n")

        f.write("## Choking Check\n\n")
        ch = values["choking"]
        f.write(f"- throat-region max Mach: {ch['throat_mach']:.6g}\n")
        f.write(f"- global max Mach: {ch['max_mach']:.6g}\n")
        f.write(f"- status: {ch['status']}\n")
        f.write(f"- note: {ch['message']}\n\n")

        f.write("## Comparison With Isentropic Theory\n\n")
        e = values["errors"]
        f.write("- reference uses isentropic air relations with `gamma = 1.4` evaluated from CFD centerline Mach number\n")
        f.write(f"- RMS error in `p/p0`: {e['p_rms_error']:.6g}\n")
        f.write(f"- RMS error in `T/T0`: {e['T_rms_error']:.6g}\n")
        f.write(f"- RMS error in `rho/rho0`: {e['rho_rms_error']:.6g}\n")
        f.write(f"- plots written to `{display_path(values['images_dir'])}`\n")
        f.write(f"- centerline CSV written to `{display_path(values['centerline_csv'])}`\n\n")

        f.write("## Area-Mach Relation Validation\n\n")
        area = values["area_mach"]
        f.write("- reference solves the quasi-1D isentropic area-Mach relation from `system/blockMeshDict`\n")
        f.write(f"- throat x-location: {area['throat_x']:.6g} m\n")
        f.write(f"- throat area proxy: {area['throat_area']:.6g} m2 per unit depth\n")
        f.write(f"- A/A* range: {area['area_ratio_min']:.6g} to {area['area_ratio_max']:.6g}\n")
        f.write(f"- RMS error in Mach over valid isentropic points: {area['rms_error']:.6g}\n")
        if not math.isnan(float(area["pre_shock_rms_error"])):
            f.write(f"- pre-shock isentropic RMS error in Mach: {area['pre_shock_rms_error']:.6g}\n")
        if not math.isnan(float(area["post_shock_rms_error"])):
            f.write(f"- post-shock isentropic RMS error in Mach: {area['post_shock_rms_error']:.6g}\n")
            f.write(f"- post-shock comparison points: {area['post_shock_points']}\n")
        f.write(f"- valid comparison points: {area['valid_points']} / {area['total_points']}\n")
        if area["shock_x"] is not None:
            f.write(f"- detected shock location: x = {area['shock_x']:.6g} m\n")
        f.write(f"- branch/masking note: {area['note']}\n")
        f.write(f"- Mach comparison plot: `{display_path(area['mach_plot'])}`\n")
        f.write(f"- area-ratio plot: `{display_path(area['area_plot'])}`\n\n")

        f.write("## Time-History Steadiness Check\n\n")
        history = values["time_history"]
        final_co = history["final_max_Courant"]
        final_mass_error = history["final_mass_error_percent"]
        variation = history["steady_variation_percent"]
        f.write(f"- final max Courant: {final_co:.6g}\n" if final_co is not None else "- final max Courant: unavailable\n")
        if final_mass_error is not None:
            f.write(f"- final mass conservation error from histories: {final_mass_error:.6g}%\n")
        else:
            f.write(f"- final mass conservation error from final fields: {values['mass_error']:.6g}%\n")
        if variation is not None:
            f.write(f"- last-10% relative variation: {variation:.6g}% using `{history['steady_signal']}`\n")
        else:
            f.write("- last-10% relative variation: unavailable\n")
        f.write(f"- steadiness classification: {history['steady_verdict']}\n")
        f.write("- criterion: `<1%` quasi-steady, `1-5%` nearly steady, `>5%` still transient\n")
        f.write(f"- Courant plot: `{display_path(history['plots']['courant_plot'])}`\n")
        f.write(f"- timestep plot: `{display_path(history['plots']['timestep_plot'])}`\n")
        f.write(f"- mass-flow plot: `{display_path(history['plots']['mass_flow_plot'])}`\n")
        f.write(f"- throat-Mach plot: `{display_path(history['plots']['throat_mach_plot'])}`\n\n")

        f.write("## Final Verdict\n\n")
        f.write(f"**{values['verdict'].upper()}**\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=Path("."))
    parser.add_argument("--time", default="latest")
    parser.add_argument("--inlet")
    parser.add_argument("--outlet")
    parser.add_argument("--p0", type=float, default=300000.0)
    parser.add_argument("--T0", type=float, default=300.0)
    parser.add_argument("--gamma", type=float, default=GAMMA)
    parser.add_argument("--R", type=float, default=R_AIR)
    parser.add_argument("--throat-x", type=float, default=0.05)
    parser.add_argument("--subsonic", action="store_true", help="Require Mach < 1 everywhere")
    parser.add_argument("--summary", type=Path, default=Path("docs/validation_summary.md"))
    parser.add_argument("--images-dir", type=Path, default=Path("docs/images"))
    parser.add_argument("--area-images-dir", type=Path, default=Path("docs/images"))
    parser.add_argument("--study-csv", type=Path, default=Path("docs/pressure_ratio_study.csv"))
    parser.add_argument("--study-markdown", type=Path, default=Path("docs/pressure_ratio_study.md"))
    parser.add_argument("--skip-pressure-study", action="store_true")
    parser.add_argument(
        "--centerline-output",
        type=Path,
        default=Path("postProcessing/centerline/centerline_latest.csv"),
    )
    args = parser.parse_args()

    case_dir = args.case.resolve()
    time_dir = latest_time(case_dir) if args.time == "latest" else case_dir / args.time
    patches = parse_boundary(case_dir / "constant/polyMesh/boundary")
    inlet_patch, outlet_patch = identify_flow_patches(patches, args.inlet, args.outlet)
    print(f"Available patches: {format_patch_list(patches)}")
    print(f"Using inlet patch: {inlet_patch}")
    print(f"Using outlet patch: {outlet_patch}")

    centerline_csv = args.centerline_output
    if not centerline_csv.is_absolute():
        centerline_csv = case_dir / centerline_csv
    write_centerline(case_dir, time_dir.name, centerline_csv, bins=500)

    mdot_in = patch_mass_flow(case_dir, time_dir, inlet_patch)
    mdot_out = patch_mass_flow(case_dir, time_dir, outlet_patch)
    mass_error = abs(abs(mdot_in) - abs(mdot_out)) / max(abs(mdot_in), abs(mdot_out), 1e-300) * 100.0
    mass_assessment = mass_flow_assessment(mass_error)

    stats = field_stats(case_dir, time_dir)
    warnings = []
    if stats["p"][0] <= 0:
        warnings.append("pressure is non-positive")
    if stats["T"][0] <= 0:
        warnings.append("temperature is non-positive")
    if stats["rho"][0] <= 0:
        warnings.append("density is non-positive")
    if stats["Ma"][1] > 5.0:
        warnings.append("Mach number is unrealistically high for this setup")
    sanity_assessment = "pass" if not warnings else "; ".join(warnings)

    rho0 = args.p0 / (args.R * args.T0)
    images_dir = args.images_dir
    if not images_dir.is_absolute():
        images_dir = case_dir / images_dir
    errors = plot_validation(centerline_csv, images_dir, args.p0, args.T0, rho0, args.gamma)
    area_images_dir = args.area_images_dir
    if not area_images_dir.is_absolute():
        area_images_dir = Path.cwd() / area_images_dir
    area_mach = validate_area_mach(
        centerline_csv=centerline_csv,
        block_mesh_dict=case_dir / "system/blockMeshDict",
        case_name=case_dir.name,
        images_dir=area_images_dir,
        gamma=args.gamma,
        throat_x=args.throat_x,
    )
    time_history = analyze_time_history(case_dir, area_images_dir, case_dir.name)
    courant = parse_courant(case_dir / "log.rhoCentralFoam")
    mesh = parse_check_mesh(case_dir / "log.checkMesh")
    cells = mesh_cell_count(case_dir)
    choking = choking_check(centerline_csv, args.throat_x, True if args.subsonic else None)
    final_verdict = verdict(mass_error, courant, mesh, stats, choking)

    values = {
        "case_dir": case_dir,
        "time_name": time_dir.name,
        "inlet_patch": inlet_patch,
        "outlet_patch": outlet_patch,
        "mdot_in": mdot_in,
        "mdot_out": mdot_out,
        "mass_error": mass_error,
        "mass_assessment": mass_assessment,
        "courant": courant,
        "mesh": mesh,
        "mesh_cells": cells,
        "stats": stats,
        "sanity_assessment": sanity_assessment,
        "choking": choking,
        "errors": errors,
        "area_mach": area_mach,
        "time_history": time_history,
        "verdict": final_verdict,
        "images_dir": images_dir,
        "centerline_csv": centerline_csv,
    }
    summary_path = args.summary
    if not summary_path.is_absolute():
        summary_path = case_dir / summary_path
    write_summary(summary_path, values)

    study_csv = args.study_csv
    study_markdown = args.study_markdown
    if not args.skip_pressure_study:
        if not study_csv.is_absolute():
            study_csv = Path.cwd() / study_csv
        if not study_markdown.is_absolute():
            study_markdown = Path.cwd() / study_markdown
        study_row = case_metadata(case_dir)
        study_row.update({
            "observed_max_Mach": format_number(choking["max_mach"]),
            "observed_throat_Mach": format_number(choking["throat_mach"]),
            "mdot_in_kg_s": format_number(mdot_in),
            "mdot_out_kg_s": format_number(mdot_out),
            "mass_error_percent": format_number(mass_error),
            "max_Courant": format_number(courant["max_max"] if courant.get("available") else None),
            "mesh_cells": str(cells),
            "validation_verdict": final_verdict,
        })
        upsert_row(study_csv, study_row)
        write_markdown(study_csv, study_markdown)

    print(f"mdot_in = {mdot_in:.8e} kg/s")
    print(f"mdot_out = {mdot_out:.8e} kg/s")
    print(f"mass conservation error = {mass_error:.4f}% ({mass_assessment})")
    if courant.get("available"):
        print(f"max Courant number = {courant['max_max']:.6g}")
    if mesh.get("available"):
        print(f"mesh passed = {mesh['passed']}")
    print(f"throat-region max Mach = {choking['throat_mach']:.6g}")
    print(f"area-Mach RMS error = {area_mach['rms_error']:.6g}")
    print(f"time-history steadiness = {time_history['steady_verdict']} ({time_history['steady_signal']})")
    print(f"final verdict = {final_verdict}")
    print(f"Wrote summary: {summary_path}")
    if not args.skip_pressure_study:
        print(f"Updated pressure-ratio study: {study_csv}")
        print(f"Updated pressure-ratio study table: {study_markdown}")


if __name__ == "__main__":
    main()

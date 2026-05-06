#!/usr/bin/env python3
"""Advanced validation from existing Laval nozzle outputs only."""

from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import numpy as np

from area_mach_validation import (
    area_mach,
    branch_for_case,
    detect_shock_region,
    interpolate_area,
    nozzle_profile,
    rms_error,
    solve_branch,
)
from plot_time_history import (
    field_based_histories,
    relative_variation,
    steady_verdict,
)
from postprocess_centerline import latest_time, write_centerline


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("subsonic", ROOT / "cases/subsonic", "subsonic"),
    ("choked", ROOT / "cases/choked", "choked"),
    ("internal_shock", ROOT / "cases/internal_shock", "internal_shock"),
]
GAMMA = 1.4


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


def log_candidates(case_dir: Path) -> list[Path]:
    candidates = []
    exact = case_dir / "log.rhoCentralFoam"
    if exact.exists():
        candidates.append(exact)
    candidates.extend(path for path in case_dir.glob("log.rhoCentralFoam.*") if path.is_file())
    return sorted(set(candidates), key=lambda path: (path.stat().st_mtime, path.name))


def parse_log_file(path: Path) -> dict[str, object]:
    records = []
    execution = []
    current_time = None
    pending_delta_t = None
    for line in path.read_text(errors="ignore").splitlines():
        dt_match = re.search(r"^deltaT\s*=\s*([-+0-9.eE]+)", line)
        if dt_match:
            pending_delta_t = float(dt_match.group(1))
            continue

        time_match = re.search(r"^Time\s*=\s*([-+0-9.eE]+)", line)
        if time_match:
            current_time = float(time_match.group(1))
            continue

        co_match = re.search(r"Mean and max Courant Numbers\s*=\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)", line)
        if co_match:
            records.append({
                "time": current_time if current_time is not None else float(len(records)),
                "deltaT": pending_delta_t,
                "mean_Courant": float(co_match.group(1)),
                "max_Courant": float(co_match.group(2)),
            })
            continue

        exec_match = re.search(r"ExecutionTime\s*=\s*([-+0-9.eE]+)\s+s", line)
        if exec_match:
            execution.append(float(exec_match.group(1)))

    return {
        "path": path,
        "records": records,
        "execution_time": execution[-1] if execution else None,
        "ended": bool(re.search(r"^End\s*$", path.read_text(errors="ignore"), re.M)),
    }


def parse_logs(case_dir: Path) -> dict[str, object]:
    parsed = [parse_log_file(path) for path in log_candidates(case_dir)]
    rows_by_time: dict[float, dict[str, object]] = {}
    for item in parsed:
        for record in item["records"]:
            time = float(record["time"])
            rows_by_time[time] = {
                "time": time,
                "deltaT": record["deltaT"],
                "mean_Courant": record["mean_Courant"],
                "max_Courant": record["max_Courant"],
                "source_log": rel(item["path"]),
            }
    rows = [rows_by_time[key] for key in sorted(rows_by_time)]
    execution_total = sum(float(item["execution_time"]) for item in parsed if item["execution_time"] is not None)
    return {
        "rows": rows,
        "logs": [rel(item["path"]) for item in parsed],
        "execution_time_s": execution_total if execution_total > 0 else None,
        "final_execution_time_s": next((item["execution_time"] for item in reversed(parsed) if item["execution_time"] is not None), None),
        "ended": any(bool(item["ended"]) for item in parsed),
    }


def series_variation(series: tuple[np.ndarray, np.ndarray] | None) -> float | None:
    if series is None:
        return None
    return relative_variation(series[1])


def final_mass_error(inlet: tuple[np.ndarray, np.ndarray] | None, outlet: tuple[np.ndarray, np.ndarray] | None) -> float | None:
    if inlet is None or outlet is None or len(inlet[0]) == 0 or len(outlet[0]) == 0:
        return None
    common_t = np.intersect1d(inlet[0], outlet[0])
    if len(common_t) == 0:
        common_t = np.array([min(float(inlet[0][-1]), float(outlet[0][-1]))])
    in_values = np.interp(common_t, inlet[0], np.abs(inlet[1]))
    out_values = np.interp(common_t, outlet[0], np.abs(outlet[1]))
    err = np.abs(in_values - out_values) / np.maximum(np.maximum(in_values, out_values), 1e-300) * 100.0
    return float(err[-1])


def numeric_time_dirs(case_dir: Path) -> list[Path]:
    times = []
    for path in case_dir.iterdir():
        if not path.is_dir() or path.name == "0":
            continue
        try:
            times.append((float(path.name), path))
        except ValueError:
            pass
    return [path for _, path in sorted(times)]


def centerline_throat_history(case_dir: Path, label: str, throat_x: float = 0.05) -> tuple[np.ndarray, np.ndarray] | None:
    rows = []
    scratch = Path("/tmp/laval_nozzle_centerline_history") / label
    scratch.mkdir(parents=True, exist_ok=True)
    for time_dir in numeric_time_dirs(case_dir):
        if not all((time_dir / field).exists() for field in ("rho", "U", "T", "p")):
            continue
        out_path = scratch / f"centerline_{time_dir.name.replace('.', '_')}.csv"
        write_centerline(case_dir, time_dir.name, out_path, bins=700)
        data = np.genfromtxt(out_path, delimiter=",", names=True)
        x = np.asarray(data["x"])
        mach = np.asarray(data["Mach"])
        region = np.abs(x - throat_x) <= 0.003
        if not np.any(region):
            region = np.abs(x - throat_x) == np.min(np.abs(x - throat_x))
        rows.append((float(time_dir.name), float(np.max(mach[region]))))
    if not rows:
        return None
    data = np.array(rows, dtype=float)
    return data[:, 0], data[:, 1]


def plot_courant(log_rows: list[dict[str, object]], output: Path) -> bool:
    if not log_rows:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    time = np.array([float(row["time"]) for row in log_rows])
    mean = np.array([float(row["mean_Courant"]) for row in log_rows])
    max_co = np.array([float(row["max_Courant"]) for row in log_rows])
    plt.figure(figsize=(8, 4.5))
    plt.plot(time, mean, label="Mean Co", linewidth=1.6)
    plt.plot(time, max_co, label="Max Co", linewidth=1.6)
    plt.axhline(0.5, color="0.25", linestyle="--", linewidth=1, label="Co = 0.5")
    plt.xlabel("Time [s]")
    plt.ylabel("Courant number [-]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def plot_delta_t(log_rows: list[dict[str, object]], output: Path) -> bool:
    rows = [row for row in log_rows if row["deltaT"] is not None]
    if not rows:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    plt.plot([float(row["time"]) for row in rows], [float(row["deltaT"]) for row in rows], linewidth=1.6)
    plt.xlabel("Time [s]")
    plt.ylabel("deltaT [s]")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def plot_mass_flow(inlet: tuple[np.ndarray, np.ndarray] | None, outlet: tuple[np.ndarray, np.ndarray] | None, output: Path) -> bool:
    if inlet is None and outlet is None:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    if inlet is not None:
        plt.plot(inlet[0], inlet[1], marker="o", label="Inlet")
    if outlet is not None:
        plt.plot(outlet[0], outlet[1], marker="o", label="Outlet")
    plt.xlabel("Written time [s]")
    plt.ylabel("Mass flow rate [kg/s]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def plot_throat_mach(series: tuple[np.ndarray, np.ndarray] | None, output: Path) -> bool:
    if series is None:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    plt.plot(series[0], series[1], marker="o", linewidth=1.8)
    plt.axhline(1.0, color="0.25", linestyle="--", linewidth=1)
    plt.xlabel("Written time [s]")
    plt.ylabel("Throat Mach number [-]")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def area_mach_case(label: str, case_dir: Path, branch_case: str) -> dict[str, object]:
    time_dir = latest_time(case_dir)
    centerline = case_dir / "postProcessing/centerline/centerline_latest.csv"
    write_centerline(case_dir, time_dir.name, centerline, bins=700)
    data = np.genfromtxt(centerline, delimiter=",", names=True)
    x = np.asarray(data["x"])
    cfd_mach = np.asarray(data["Mach"])

    geom_x, geom_area = nozzle_profile(case_dir / "system/blockMeshDict")
    throat_i = int(np.argmin(geom_area))
    throat_x = float(geom_x[throat_i])
    throat_area = float(np.min(geom_area))
    area = interpolate_area(x, geom_x, geom_area)
    area_ratio = area / throat_area
    sub_branch = solve_branch(area_ratio, False, GAMMA)
    sup_branch = solve_branch(area_ratio, True, GAMMA)
    theory, valid, note, shock_x, shock_mask = branch_for_case(
        branch_case, x, area_ratio, sub_branch, sup_branch, throat_x, cfd_mach
    )
    error = rms_error(cfd_mach, theory, valid)

    pre_shock_error = float("nan")
    post_shock_error = float("nan")
    post_shock_points = 0
    post_theory = None
    if branch_case == "internal_shock" and shock_x is not None:
        pre_shock_error = rms_error(cfd_mach, theory, valid & (x < shock_x))
        post_valid = (x > shock_x) & ~shock_mask & (cfd_mach < 0.95)
        post_shock_points = int(np.count_nonzero(post_valid))
        if post_shock_points >= 3:
            effective_a_star = np.median(area[post_valid] / area_mach(cfd_mach[post_valid], GAMMA))
            post_area_ratio = np.maximum(area / effective_a_star, 1.0)
            post_theory = solve_branch(post_area_ratio, False, GAMMA)
            post_shock_error = rms_error(cfd_mach, post_theory, post_valid)

    output = ROOT / "docs/images" / f"{label}_area_mach_validation.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(9, 7.2), sharex=True)
    axes[0].plot(x, area_ratio, color="black", linewidth=2)
    axes[0].axvline(throat_x, color="0.3", linestyle="--", linewidth=1, label="throat")
    if shock_x is not None:
        axes[0].axvspan(float(x[shock_mask].min()), float(x[shock_mask].max()), color="tab:red", alpha=0.15, label="masked shock region")
    axes[0].set_ylabel("A(x) / A* [-]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    axes[1].plot(x, cfd_mach, label="CFD centerline", linewidth=2)
    axes[1].plot(x, sub_branch, "--", label="subsonic branch", linewidth=1.5)
    axes[1].plot(x, sup_branch, "--", label="supersonic branch", linewidth=1.5)
    axes[1].plot(x[valid], theory[valid], color="black", linewidth=1.4, label="selected isentropic comparison")
    if np.any(~valid):
        axes[1].scatter(x[~valid], cfd_mach[~valid], s=12, color="tab:red", label="masked CFD points")
    if post_theory is not None:
        post_valid = (x > shock_x) & ~shock_mask & (cfd_mach < 0.95)
        axes[1].plot(x[post_valid], post_theory[post_valid], color="tab:green", linewidth=1.4, label="post-shock fitted subsonic branch")
    if shock_x is not None:
        axes[1].axvline(shock_x, color="tab:red", linestyle=":", linewidth=1.5, label="detected shock")
    axes[1].axvline(throat_x, color="0.3", linestyle="--", linewidth=1)
    axes[1].set_xlabel("x [m]")
    axes[1].set_ylabel("Mach number [-]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best", fontsize=8)
    fig.suptitle(label.replace("_", " ").title() + " Area-Mach Validation")
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)

    return {
        "case": label,
        "case_dir": rel(case_dir),
        "latest_time": time_dir.name,
        "centerline_csv": rel(centerline),
        "throat_x_m": throat_x,
        "throat_area_proxy_m2_per_depth": throat_area,
        "area_ratio_min": float(np.min(area_ratio)),
        "area_ratio_max": float(np.max(area_ratio)),
        "cfd_throat_mach": float(np.max(cfd_mach[np.abs(x - throat_x) <= 0.003])),
        "cfd_max_mach": float(np.max(cfd_mach)),
        "rms_error": error,
        "pre_shock_rms_error": pre_shock_error,
        "post_shock_rms_error": post_shock_error,
        "valid_points": int(np.count_nonzero(valid)),
        "masked_points": int(np.count_nonzero(~valid)),
        "total_points": int(len(valid)),
        "shock_x_m": shock_x,
        "post_shock_points": post_shock_points,
        "note": note,
        "plot": rel(output),
    }


def time_history_case(label: str, case_dir: Path) -> dict[str, object]:
    logs = parse_logs(case_dir)
    histories = field_based_histories(case_dir)
    inlet = histories.get("inlet")
    outlet = histories.get("outlet")
    throat = centerline_throat_history(case_dir, label)
    mass_error = final_mass_error(inlet, outlet)

    image_dir = ROOT / "docs/images"
    courant_plot = image_dir / f"{label}_courant_history.png"
    timestep_plot = image_dir / f"{label}_timestep_history.png"
    mass_plot = image_dir / f"{label}_mass_flow_history.png"
    throat_plot = image_dir / f"{label}_throat_mach_history.png"
    plot_courant(logs["rows"], courant_plot)
    plot_delta_t(logs["rows"], timestep_plot)
    plot_mass_flow(inlet, outlet, mass_plot)
    plot_throat_mach(throat, throat_plot)

    max_co_values = [float(row["max_Courant"]) for row in logs["rows"]]
    dt_values = [float(row["deltaT"]) for row in logs["rows"] if row["deltaT"] is not None]
    steady_source = None
    steady_label = "none"
    if outlet is not None and len(outlet[1]) >= 2:
        steady_source = outlet[1]
        steady_label = "outlet mass flow from written fields"
    elif throat is not None and len(throat[1]) >= 2:
        steady_source = throat[1]
        steady_label = "throat Mach from written fields"
    elif max_co_values:
        steady_source = np.asarray(max_co_values)
        steady_label = "max Courant from log"
    variation, steady = steady_verdict(np.asarray(steady_source)) if steady_source is not None else (None, "insufficient data")

    return {
        "case": label,
        "case_dir": rel(case_dir),
        "logs_parsed": ";".join(logs["logs"]),
        "log_samples": len(logs["rows"]),
        "field_time_samples": len(outlet[0]) if outlet is not None else 0,
        "throat_mach_samples": len(throat[0]) if throat is not None else 0,
        "final_log_time": max((float(row["time"]) for row in logs["rows"]), default=float("nan")),
        "final_deltaT": dt_values[-1] if dt_values else None,
        "min_deltaT": min(dt_values) if dt_values else None,
        "max_deltaT": max(dt_values) if dt_values else None,
        "final_max_Courant": max_co_values[-1] if max_co_values else None,
        "max_Courant": max(max_co_values) if max_co_values else None,
        "execution_time_s": logs["execution_time_s"],
        "final_execution_time_s": logs["final_execution_time_s"],
        "ended": logs["ended"],
        "final_mdot_in_kg_s": float(inlet[1][-1]) if inlet is not None else None,
        "final_mdot_out_kg_s": float(outlet[1][-1]) if outlet is not None else None,
        "final_mass_error_percent": mass_error,
        "final_throat_mach": float(throat[1][-1]) if throat is not None else None,
        "steady_signal": steady_label,
        "steady_variation_percent": variation,
        "steady_verdict": steady,
        "courant_plot": rel(courant_plot),
        "mass_flow_plot": rel(mass_plot),
        "throat_mach_plot": rel(throat_plot),
        "limitation": "Histories from fields are limited to written time directories; solver log contains many more time-step samples.",
    }


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                column: str(row.get(column)) if isinstance(row.get(column), int)
                else fmt(row.get(column)) if isinstance(row.get(column), float) or row.get(column) is None
                else row.get(column, "")
                for column in columns
            })


def display(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (float, int)):
        return fmt(value)
    return str(value)


def write_area_doc(rows: list[dict[str, object]]) -> None:
    columns = ["case", "latest_time", "cfd_throat_mach", "cfd_max_mach", "rms_error", "pre_shock_rms_error", "post_shock_rms_error", "valid_points", "masked_points", "shock_x_m", "plot"]
    with (ROOT / "docs/area_mach_validation.md").open("w") as f:
        f.write("# Area-Mach Validation\n\n")
        f.write("Generated from existing latest-time fields only. Centerline data are extracted from OpenFOAM ASCII fields; nozzle `A(x)/A*` is reconstructed from `system/blockMeshDict`; both subsonic and supersonic branches of the quasi-1D isentropic area-Mach relation are solved numerically.\n\n")
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(display(row.get(column)).replace("|", "\\|") for column in columns) + " |\n")
        f.write("\n## Notes\n\n")
        f.write("- The subsonic case is compared against the subsonic branch over the full nozzle.\n")
        f.write("- The choked case uses the subsonic branch upstream of the throat and the supersonic branch downstream.\n")
        f.write("- The internal-shock case masks the detected shock region and does not apply geometric-throat isentropic theory through the shock. Post-shock comparison, where reported, uses a fitted downstream subsonic branch because entropy has changed across the shock.\n")
        f.write("- The geometry is quasi-2D, so the area is an area proxy per unit depth reconstructed from nozzle height.\n")


def write_time_doc(rows: list[dict[str, object]]) -> None:
    columns = ["case", "log_samples", "field_time_samples", "throat_mach_samples", "final_log_time", "final_deltaT", "max_Courant", "final_max_Courant", "execution_time_s", "final_mass_error_percent", "final_throat_mach", "steady_signal", "steady_variation_percent", "steady_verdict"]
    with (ROOT / "docs/time_history_assessment.md").open("w") as f:
        f.write("# Time-History Assessment\n\n")
        f.write("Generated from existing solver logs and written time folders only. Log histories provide `time`, `deltaT`, Courant number, and execution time. Mass-flow and throat-Mach histories are recomputed from written time directories using existing `rho`, `U`, and `T` fields.\n\n")
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(display(row.get(column)).replace("|", "\\|") for column in columns) + " |\n")
        f.write("\n## Limitations\n\n")
        f.write("- Field-based mass-flow and throat-Mach histories have only as many samples as saved time directories, not every solver step.\n")
        f.write("- Restarted or alternate solver logs are merged by time where possible; execution time is reported from parsed logs and can include restart segments when present.\n")
        f.write("- No convergence claim is made from unsaved intermediate fields.\n")


def update_readme(area_rows: list[dict[str, object]], time_rows: list[dict[str, object]]) -> None:
    path = ROOT / "README.md"
    text = path.read_text()
    block = """## Advanced Validation Artifacts\n\nThe advanced validation pass uses existing outputs only and adds centerline area-Mach and time-history diagnostics:\n\n- `docs/area_mach_validation.md`\n- `docs/time_history_assessment.md`\n- `docs/data/area_mach_validation_summary.csv`\n- `docs/data/time_history_summary.csv`\n- `docs/images/subsonic_area_mach_validation.png`\n- `docs/images/choked_area_mach_validation.png`\n- `docs/images/internal_shock_area_mach_validation.png`\n- `docs/images/*_courant_history.png`\n- `docs/images/*_mass_flow_history.png`\n\nInternal-shock area-Mach validation masks the detected shock region and does not apply isentropic theory through the shock. Mass-flow histories are recomputed from written time folders using `rho` and `U`, so their temporal resolution is limited by write intervals.\n"""
    marker = "\n## Advanced Validation Artifacts\n"
    if marker in text:
        text = text[: text.index(marker)] + "\n" + block
    else:
        text = text.rstrip() + "\n\n" + block
    path.write_text(text)


def update_report(area_rows: list[dict[str, object]], time_rows: list[dict[str, object]]) -> None:
    path = ROOT / "report/laval_nozzle_report.tex"
    text = path.read_text()
    area_lines = "\n".join(
        rf"\texttt{{{row['case'].replace('_', r'\_')}}} & {fmt(row['rms_error'])} & {int(row['valid_points'])}/{int(row['total_points'])} & {fmt(row['shock_x_m'])} \\"
        for row in area_rows
    )
    time_lines = "\n".join(
        rf"\texttt{{{row['case'].replace('_', r'\_')}}} & {int(row['log_samples'])} & {int(row['field_time_samples'])} & {fmt(row['max_Courant'])} & {fmt(row['final_mass_error_percent'])}\% & {row['steady_verdict']} \\"
        for row in time_rows
    )
    advanced = rf"""
\section{{Advanced Validation}}
The advanced pass extracts centerline data, reconstructs \(A(x)/A^*\) from the nozzle geometry, solves the subsonic and supersonic area-Mach branches, and compares CFD Mach against the applicable branch. The internal-shock case masks the detected shock region and does not apply isentropic theory through entropy-producing shock cells.

\begin{{table}}[h]
\centering
\caption{{Area-Mach comparison summary.}}
\begin{{tabular}}{{lccc}}
\toprule
Case & RMS Mach error & Valid points & Shock x [m] \\
\midrule
{area_lines}
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{table}}[h]
\centering
\caption{{Time-history summary from logs and written fields.}}
\begin{{tabular}}{{lccccc}}
\toprule
Case & Log samples & Field samples & Max Co & Final mass error & Steadiness \\
\midrule
{time_lines}
\bottomrule
\end{{tabular}}
\end{{table}}

Mass-flow histories are recomputed from written folders using \(\rho\) and \(\mathbf{{U}}\). Their time resolution is therefore limited by write intervals, while Courant and \(\Delta t\) histories come from solver logs.
"""
    if "\\section{Advanced Validation}" in text:
        start = text.index("\\section{Advanced Validation}")
        end = text.index("\\section{Generated Artifacts}") if "\\section{Generated Artifacts}" in text[start:] else text.index("\\end{document}")
        text = text[:start] + advanced + "\n" + text[end:]
    else:
        text = text.replace("\\section{Generated Artifacts}", advanced + "\n\\section{Generated Artifacts}")

    for item in [
        r"\item \texttt{docs/area\_mach\_validation.md}",
        r"\item \texttt{docs/time\_history\_assessment.md}",
        r"\item \texttt{docs/data/area\_mach\_validation\_summary.csv}",
        r"\item \texttt{docs/data/time\_history\_summary.csv}",
    ]:
        if item not in text:
            text = text.replace(r"\item \texttt{docs/validation\_summary.md}", item + "\n" + r"\item \texttt{docs/validation\_summary.md}")
    path.write_text(text)


def main() -> None:
    area_rows = [area_mach_case(label, case_dir, branch_case) for label, case_dir, branch_case in CASES]
    time_rows = [time_history_case(label, case_dir) for label, case_dir, _ in CASES]
    area_columns = [
        "case", "case_dir", "latest_time", "centerline_csv", "throat_x_m", "throat_area_proxy_m2_per_depth",
        "area_ratio_min", "area_ratio_max", "cfd_throat_mach", "cfd_max_mach", "rms_error",
        "pre_shock_rms_error", "post_shock_rms_error", "valid_points", "masked_points", "total_points",
        "shock_x_m", "post_shock_points", "note", "plot",
    ]
    time_columns = [
        "case", "case_dir", "logs_parsed", "log_samples", "field_time_samples", "throat_mach_samples",
        "final_log_time", "final_deltaT", "min_deltaT", "max_deltaT", "final_max_Courant", "max_Courant",
        "execution_time_s", "final_execution_time_s", "ended", "final_mdot_in_kg_s", "final_mdot_out_kg_s",
        "final_mass_error_percent", "final_throat_mach", "steady_signal", "steady_variation_percent",
        "steady_verdict", "courant_plot", "mass_flow_plot", "throat_mach_plot", "limitation",
    ]
    write_csv(ROOT / "docs/data/area_mach_validation_summary.csv", area_rows, area_columns)
    write_csv(ROOT / "docs/data/time_history_summary.csv", time_rows, time_columns)
    write_area_doc(area_rows)
    write_time_doc(time_rows)
    update_readme(area_rows, time_rows)
    update_report(area_rows, time_rows)
    print("Advanced validation complete:")
    for row in area_rows:
        print(f"{row['case']}: area-Mach RMS={row['rms_error']:.6g}, valid={row['valid_points']}/{row['total_points']}, shock_x={fmt(row['shock_x_m'])}")
    for row in time_rows:
        print(f"{row['case']}: log samples={row['log_samples']}, field samples={row['field_time_samples']}, maxCo={fmt(row['max_Courant'])}, steady={row['steady_verdict']}")


if __name__ == "__main__":
    main()

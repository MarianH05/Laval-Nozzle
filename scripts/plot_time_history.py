#!/usr/bin/env python3
"""Plot time-history diagnostics from OpenFOAM logs and postProcessing files."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import numpy as np

from postprocess_centerline import (
    GAMMA,
    R_AIR,
    read_faces,
    read_labels,
    read_points,
    read_scalar_field,
    read_vector_field,
)


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def relative_variation(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return None
    tail = values[max(0, int(0.9 * len(values))) :]
    if len(tail) < 2:
        tail = values
    scale = max(abs(float(np.mean(tail))), 1e-300)
    return float((np.max(tail) - np.min(tail)) / scale * 100.0)


def steady_verdict(values: np.ndarray) -> tuple[float | None, str]:
    variation = relative_variation(values)
    if variation is None:
        return None, "insufficient data"
    if variation < 1.0:
        return variation, "quasi-steady"
    if variation <= 5.0:
        return variation, "nearly steady"
    return variation, "still transient"


def parse_solver_log(log_path: Path) -> dict[str, np.ndarray]:
    if not log_path.exists():
        warn(f"solver log not found: {log_path}")
        return {}

    times = []
    courant_times = []
    mean_co = []
    max_co = []
    delta_t_times = []
    delta_t = []
    current_time = None

    for line in log_path.read_text(errors="ignore").splitlines():
        time_match = re.search(r"^Time\s*=\s*([-+0-9.eE]+)", line)
        if time_match:
            current_time = float(time_match.group(1))
            times.append(current_time)
            continue

        dt_match = re.search(r"^deltaT\s*=\s*([-+0-9.eE]+)", line)
        if dt_match:
            delta_t_times.append(current_time if current_time is not None else len(delta_t) + 1)
            delta_t.append(float(dt_match.group(1)))
            continue

        co_match = re.search(r"Mean and max Courant Numbers\s*=\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)", line)
        if co_match:
            courant_times.append(current_time if current_time is not None else len(max_co) + 1)
            mean_co.append(float(co_match.group(1)))
            max_co.append(float(co_match.group(2)))

    result = {}
    if max_co:
        result["courant_time"] = np.array(courant_times, dtype=float)
        result["mean_Courant"] = np.array(mean_co, dtype=float)
        result["max_Courant"] = np.array(max_co, dtype=float)
    else:
        warn(f"no Courant entries found in {log_path}")

    if delta_t:
        result["deltaT_time"] = np.array(delta_t_times, dtype=float)
        result["deltaT"] = np.array(delta_t, dtype=float)
    else:
        warn(f"no deltaT entries found in {log_path}")

    return result


def read_numeric_table(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    rows = []
    for line in path.read_text(errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", stripped)
        if len(values) >= 2:
            rows.append([float(value) for value in values])
    if not rows:
        return None
    width = max(len(row) for row in rows)
    padded = [row + [np.nan] * (width - len(row)) for row in rows]
    data = np.array(padded, dtype=float)
    return data[:, 0], data[:, -1]


def find_series(case_dir: Path, names: tuple[str, ...], files: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray, Path] | None:
    post = case_dir / "postProcessing"
    if not post.exists():
        return None
    candidates = []
    for path in post.rglob("*"):
        if not path.is_file():
            continue
        lowered = str(path.relative_to(post)).lower()
        if any(name.lower() in lowered for name in names) and (not files or path.name in files):
            candidates.append(path)
    for path in sorted(candidates):
        series = read_numeric_table(path)
        if series is not None and len(series[0]) > 0:
            return series[0], series[1], path
    return None


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


def mesh_data(case_dir: Path) -> dict[str, object] | None:
    poly = case_dir / "constant/polyMesh"
    required = [poly / name for name in ("boundary", "faces", "points", "owner", "neighbour")]
    if not all(path.exists() for path in required):
        return None
    owner = read_labels(poly / "owner")
    neighbour = read_labels(poly / "neighbour")
    return {
        "patches": parse_boundary(poly / "boundary"),
        "faces": read_faces(poly / "faces"),
        "points": read_points(poly / "points"),
        "owner": owner,
        "n_cells": int(max(owner.max(), neighbour.max())) + 1,
    }


def patch_mass_flow_from_fields(mesh: dict[str, object], time_dir: Path, patch_name: str) -> float:
    patches = mesh["patches"]
    patch = patches[patch_name]
    faces = mesh["faces"]
    points = mesh["points"]
    owner = mesh["owner"]
    n_cells = int(mesh["n_cells"])
    rho = read_scalar_field(time_dir / "rho", n_cells)
    U = read_vector_field(time_dir / "U", n_cells)

    start = int(patch["startFace"])
    stop = start + int(patch["nFaces"])
    mdot = 0.0
    for face_i in range(start, stop):
        cell_i = owner[face_i]
        area_vec = face_area_vector(points[faces[face_i]])
        mdot += rho[cell_i] * float(np.dot(U[cell_i], area_vec))
    return mdot


def patch_area_average_scalar(mesh: dict[str, object], time_dir: Path, patch_name: str, field_name: str) -> float:
    patches = mesh["patches"]
    patch = patches[patch_name]
    faces = mesh["faces"]
    points = mesh["points"]
    owner = mesh["owner"]
    n_cells = int(mesh["n_cells"])
    field = read_scalar_field(time_dir / field_name, n_cells)

    start = int(patch["startFace"])
    stop = start + int(patch["nFaces"])
    weighted = 0.0
    total_area = 0.0
    for face_i in range(start, stop):
        cell_i = owner[face_i]
        area = float(np.linalg.norm(face_area_vector(points[faces[face_i]])))
        weighted += field[cell_i] * area
        total_area += area
    return weighted / max(total_area, 1e-300)


def throat_mach_from_fields(mesh: dict[str, object], time_dir: Path, throat_x: float = 0.05) -> float:
    n_cells = int(mesh["n_cells"])
    T = read_scalar_field(time_dir / "T", n_cells)
    U = read_vector_field(time_dir / "U", n_cells)
    mach = np.linalg.norm(U, axis=1) / np.sqrt(GAMMA * R_AIR * T)

    faces = mesh["faces"]
    points = mesh["points"]
    owner = mesh["owner"]
    centres = np.zeros((n_cells, 3))
    counts = np.zeros(n_cells)
    face_centres = np.array([points[face].mean(axis=0) for face in faces])
    for face_i, cell_i in enumerate(owner):
        centres[cell_i] += face_centres[face_i]
        counts[cell_i] += 1
    centres /= np.maximum(counts[:, None], 1.0)

    region = np.abs(centres[:, 0] - throat_x) <= 0.003
    if not np.any(region):
        region = np.abs(centres[:, 0] - throat_x) == np.min(np.abs(centres[:, 0] - throat_x))
    return float(np.max(mach[region]))


def field_based_histories(case_dir: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    mesh = mesh_data(case_dir)
    if mesh is None:
        warn("skipping field-derived histories; mesh files are unavailable")
        return {}
    patches = mesh["patches"]
    inlet = next((name for name in patches if "inlet" in name.lower()), None)
    outlet = next((name for name in patches if "outlet" in name.lower()), None)
    if inlet is None or outlet is None:
        warn("skipping field-derived histories; inlet/outlet patches were not identified")
        return {}

    rows = {"inlet": [], "outlet": [], "throat": [], "pout": []}
    for time_dir in numeric_time_dirs(case_dir):
        if not all((time_dir / field).exists() for field in ("rho", "U", "T", "p")):
            continue
        time = float(time_dir.name)
        rows["inlet"].append((time, patch_mass_flow_from_fields(mesh, time_dir, inlet)))
        rows["outlet"].append((time, patch_mass_flow_from_fields(mesh, time_dir, outlet)))
        rows["throat"].append((time, throat_mach_from_fields(mesh, time_dir)))
        rows["pout"].append((time, patch_area_average_scalar(mesh, time_dir, outlet, "p")))

    histories = {}
    for key, values in rows.items():
        if values:
            data = np.array(values, dtype=float)
            histories[key] = (data[:, 0], data[:, 1])
    return histories


def plot_courant(history: dict[str, np.ndarray], output: Path) -> bool:
    if "max_Courant" not in history:
        warn("skipping Courant plot; no Courant history available")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    plt.plot(history["courant_time"], history["mean_Courant"], label="Mean Co")
    plt.plot(history["courant_time"], history["max_Courant"], label="Max Co")
    plt.axhline(0.5, color="k", linestyle="--", linewidth=1, label="Preferred target")
    plt.xlabel("Time [s]")
    plt.ylabel("Courant number [-]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def plot_timestep(history: dict[str, np.ndarray], output: Path) -> bool:
    if "deltaT" not in history:
        warn("skipping timestep plot; no deltaT history available")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    plt.plot(history["deltaT_time"], history["deltaT"], linewidth=2)
    plt.xlabel("Time [s]")
    plt.ylabel("deltaT [s]")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def plot_mass_flow(inlet: tuple[np.ndarray, np.ndarray] | None, outlet: tuple[np.ndarray, np.ndarray] | None, output: Path) -> bool:
    if inlet is None and outlet is None:
        warn("skipping mass-flow plot; no inlet/outlet mass-flow history available")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    if inlet is not None:
        plt.plot(inlet[0], inlet[1], label="Inlet")
    if outlet is not None:
        plt.plot(outlet[0], outlet[1], label="Outlet")
    plt.xlabel("Time [s]")
    plt.ylabel("Mass flow rate [kg/s]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def plot_single(series: tuple[np.ndarray, np.ndarray] | None, output: Path, ylabel: str, label: str) -> bool:
    if series is None:
        warn(f"skipping {label} plot; no history available")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    plt.plot(series[0], series[1], linewidth=2)
    plt.xlabel("Time [s]")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return True


def analyze_time_history(case_dir: Path, images_dir: Path, case_name: str | None = None) -> dict[str, object]:
    case_name = case_name or case_dir.name
    log_history = parse_solver_log(case_dir / "log.rhoCentralFoam")

    inlet = find_series(case_dir, ("massFlowInlet", "inletMassFlow", "inlet"), ("surfaceFieldValue.dat",))
    outlet = find_series(case_dir, ("massFlowOutlet", "outletMassFlow", "outlet"), ("surfaceFieldValue.dat",))
    throat_mach = find_series(case_dir, ("throatMach", "machThroat"), ("Ma", "probes.dat", "0"))
    outlet_pressure = find_series(case_dir, ("outletPressure", "pressureOutlet"), ("surfaceFieldValue.dat",))
    field_histories = field_based_histories(case_dir)

    inlet_series = (inlet[0], inlet[1]) if inlet else field_histories.get("inlet")
    outlet_series = (outlet[0], outlet[1]) if outlet else field_histories.get("outlet")
    throat_series = (throat_mach[0], throat_mach[1]) if throat_mach else field_histories.get("throat")
    pressure_series = (outlet_pressure[0], outlet_pressure[1]) if outlet_pressure else field_histories.get("pout")

    outputs = {
        "courant_plot": images_dir / f"{case_name}_courant_history.png",
        "timestep_plot": images_dir / f"{case_name}_timestep_history.png",
        "mass_flow_plot": images_dir / f"{case_name}_mass_flow_history.png",
        "throat_mach_plot": images_dir / f"{case_name}_throat_mach_history.png",
        "outlet_pressure_plot": images_dir / f"{case_name}_outlet_pressure_history.png",
    }

    written = {
        "courant": plot_courant(log_history, outputs["courant_plot"]),
        "timestep": plot_timestep(log_history, outputs["timestep_plot"]),
        "mass_flow": plot_mass_flow(inlet_series, outlet_series, outputs["mass_flow_plot"]),
        "throat_mach": plot_single(throat_series, outputs["throat_mach_plot"], "Throat Mach number [-]", "throat Mach"),
        "outlet_pressure": plot_single(pressure_series, outputs["outlet_pressure_plot"], "Outlet pressure average [Pa]", "outlet pressure"),
    }

    mass_error_history = None
    if inlet_series is not None and outlet_series is not None:
        common_t = np.intersect1d(inlet_series[0], outlet_series[0])
        if len(common_t) >= 2:
            in_values = np.interp(common_t, inlet_series[0], np.abs(inlet_series[1]))
            out_values = np.interp(common_t, outlet_series[0], np.abs(outlet_series[1]))
            mass_error_history = np.abs(in_values - out_values) / np.maximum(in_values, 1e-300) * 100.0

    steady_source_name = None
    steady_source = None
    for name, series in (
        ("mass conservation error", mass_error_history),
        ("outlet mass flow", outlet_series[1] if outlet_series is not None else None),
        ("max Courant", log_history.get("max_Courant")),
        ("throat Mach", throat_series[1] if throat_series is not None else None),
    ):
        if series is not None and len(series) >= 2:
            steady_source_name = name
            steady_source = np.asarray(series, dtype=float)
            break

    variation, steady = steady_verdict(steady_source) if steady_source is not None else (None, "insufficient data")
    return {
        "final_max_Courant": float(log_history["max_Courant"][-1]) if "max_Courant" in log_history else None,
        "final_deltaT": float(log_history["deltaT"][-1]) if "deltaT" in log_history else None,
        "final_mass_error_percent": float(mass_error_history[-1]) if mass_error_history is not None and len(mass_error_history) else None,
        "steady_variation_percent": variation,
        "steady_verdict": steady,
        "steady_signal": steady_source_name or "none",
        "plots": outputs,
        "written": written,
        "sources": {
            "inlet_mass_flow": str(inlet[2]) if inlet else "",
            "outlet_mass_flow": str(outlet[2]) if outlet else "",
            "throat_mach": str(throat_mach[2]) if throat_mach else "",
            "outlet_pressure": str(outlet_pressure[2]) if outlet_pressure else "",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=Path("."))
    parser.add_argument("--images-dir", type=Path, default=Path("docs/images"))
    parser.add_argument("--case-name")
    args = parser.parse_args()

    result = analyze_time_history(args.case.resolve(), args.images_dir, args.case_name)
    for key, path in result["plots"].items():
        if result["written"].get(key.replace("_plot", ""), False):
            print(f"Wrote {path}")
    print(f"steady-state verdict: {result['steady_verdict']} ({result['steady_signal']})")


if __name__ == "__main__":
    main()

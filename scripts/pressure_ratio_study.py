#!/usr/bin/env python3
"""Maintain the Laval nozzle pressure-ratio study CSV and Markdown table."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


COLUMNS = [
    "case_name",
    "p0_Pa",
    "T0_K",
    "pb_Pa",
    "pb_over_p0",
    "expected_regime",
    "observed_max_Mach",
    "observed_throat_Mach",
    "mdot_in_kg_s",
    "mdot_out_kg_s",
    "mass_error_percent",
    "max_Courant",
    "mesh_cells",
    "validation_verdict",
]


DEFAULT_CASES = [
    Path("cases/subsonic"),
    Path("cases/choked"),
    Path("cases/internal_shock"),
]


def foam_uniform_scalar(path: Path, keyword: str) -> float | None:
    if not path.exists():
        return None
    text = path.read_text()
    match = re.search(rf"\b{re.escape(keyword)}\s+uniform\s+([-+0-9.eE]+)\s*;", text)
    return float(match.group(1)) if match else None


def outlet_pressure(path: Path) -> float | None:
    if not path.exists():
        return None
    text = path.read_text()
    match = re.search(
        r"\boutlet\s*\{(?P<body>.*?)\n\s*\}",
        text,
        re.S,
    )
    if not match:
        return None
    value = re.search(r"\bvalue\s+uniform\s+([-+0-9.eE]+)\s*;", match.group("body"))
    return float(value.group(1)) if value else None


def expected_regime(case_dir: Path) -> str:
    info = case_dir / "case_info.md"
    if info.exists():
        text = info.read_text()
        match = re.search(r"Expected flow regime:\s*(.+)", text)
        if match:
            return match.group(1).strip().rstrip(".")
    return case_dir.name.replace("_", " ")


def format_number(value: object, digits: int = 6) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == 0:
        return "0"
    if abs(number) >= 1e5 or abs(number) < 1e-3:
        return f"{number:.{digits}e}"
    return f"{number:.{digits}g}"


def case_metadata(case_dir: Path) -> dict[str, str]:
    p0 = foam_uniform_scalar(case_dir / "0/p", "p0")
    t0 = foam_uniform_scalar(case_dir / "0/T", "T0")
    pb = outlet_pressure(case_dir / "0/p")
    return {
        "case_name": case_dir.name,
        "p0_Pa": format_number(p0),
        "T0_K": format_number(t0),
        "pb_Pa": format_number(pb),
        "pb_over_p0": format_number(pb / p0 if p0 and pb is not None else None),
        "expected_regime": expected_regime(case_dir),
        "observed_max_Mach": "",
        "observed_throat_Mach": "",
        "mdot_in_kg_s": "",
        "mdot_out_kg_s": "",
        "mass_error_percent": "",
        "max_Courant": "",
        "mesh_cells": "",
        "validation_verdict": "",
    }


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="") as f:
        return [{column: row.get(column, "") for column in COLUMNS} for row in csv.DictReader(f)]


def write_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([{column: row.get(column, "") for column in COLUMNS} for row in rows])


def sort_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    order = {path.name: i for i, path in enumerate(DEFAULT_CASES)}
    return sorted(rows, key=lambda row: (order.get(row["case_name"], 999), row["case_name"]))


def upsert_row(csv_path: Path, row: dict[str, str]) -> None:
    rows = read_rows(csv_path)
    by_name = {existing["case_name"]: existing for existing in rows}
    by_name[row["case_name"]] = {column: row.get(column, "") for column in COLUMNS}
    write_rows(csv_path, sort_rows(list(by_name.values())))


def seed_study(csv_path: Path, case_dirs: list[Path]) -> None:
    rows = {row["case_name"]: row for row in read_rows(csv_path)}
    for case_dir in case_dirs:
        metadata = case_metadata(case_dir)
        existing = rows.get(metadata["case_name"], {})
        merged = metadata | {
            column: existing[column]
            for column in COLUMNS
            if column in existing and existing[column] and column.startswith(("observed_", "mdot_", "mass_", "max_", "mesh_", "validation_"))
        }
        rows[metadata["case_name"]] = merged
    write_rows(csv_path, sort_rows(list(rows.values())))


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def write_markdown(csv_path: Path, md_path: Path) -> None:
    rows = read_rows(csv_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open("w") as f:
        f.write("# Pressure-Ratio Study\n\n")
        f.write("| " + " | ".join(COLUMNS) + " |\n")
        f.write("| " + " | ".join(["---"] * len(COLUMNS)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(markdown_escape(row.get(column, "")) for column in COLUMNS) + " |\n")
        f.write("\n")
        f.write("## Interpretation\n\n")
        f.write(
            "The prescribed reservoir state is held fixed while the outlet static pressure is reduced. "
            "High `pb/p0` keeps the nozzle fully subsonic. Near the ideal critical ratio for air, "
            "`pb/p0 = 0.528`, the throat reaches approximately Mach 1 and the mass flow becomes choked. "
            "Further reduction of `pb/p0` permits supersonic acceleration in the divergent section; "
            "if the back pressure remains above the shock-free supersonic exit pressure, the solution "
            "adjusts through a normal shock inside the divergent section.\n\n"
        )
        f.write(
            "Observed columns are populated only by `scripts/validate_case.py` from OpenFOAM output. "
            "Blank observed entries mean that the corresponding case has not yet been validated from computed results.\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("docs/pressure_ratio_study.csv"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/pressure_ratio_study.md"))
    parser.add_argument("--case", action="append", type=Path, dest="cases")
    args = parser.parse_args()

    cases = args.cases or DEFAULT_CASES
    seed_study(args.csv, cases)
    write_markdown(args.csv, args.markdown)
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.markdown}")


if __name__ == "__main__":
    main()

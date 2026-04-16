#!/usr/bin/env python3
"""
motion_garage_timescale.py

Extract occupancy motion intervals and garage door states from Advantage Air
JSON-line logs, then plot both on a shared local-time axis.

Usage:
  python motion_garage_timescale.py file.log [file2.log ...]
  python motion_garage_timescale.py file.log --tz Australia/Perth
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import pytz


def safe_json_from_line(line: str):
    """Extract trailing JSON object from a line; return dict or None."""
    m = re.search(r"\{.*\}$", line.strip())
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def parse_timestamp_utc(ts: str):
    """
    Parse timestamps like '2025/11/06 01:11:55,464' as naive UTC datetime.
    Return None if malformed.
    """
    for fmt in ("%Y/%m/%d %H:%M:%S,%f", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            pass
    return None


def parse_motion_and_garage(path: Path):
    """Return occupancy and garage DataFrames with UTC timestamps."""
    occ_rows = []
    garage_rows = []

    text = path.read_text(encoding="utf-8", errors="ignore")
    for ln in text.splitlines():
        obj = safe_json_from_line(ln)
        if not obj:
            continue

        ts = parse_timestamp_utc(obj.get("id", ""))
        if ts is None:
            continue

        occ = obj.get("occupancySensors")
        if isinstance(occ, dict):
            for sid, payload in occ.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    row["motionDetected"] = payload.get("motionDetected")
                occ_rows.append(row)

        gd = obj.get("garageDoors")
        if isinstance(gd, dict):
            for sid, payload in gd.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        if k != "id":
                            row[k] = v
                garage_rows.append(row)

    occ_df = pd.DataFrame.from_records(occ_rows) if occ_rows else pd.DataFrame()
    garage_df = pd.DataFrame.from_records(garage_rows) if garage_rows else pd.DataFrame()
    return occ_df, garage_df


def localize(df, col="dt_utc", tz_name="Australia/Perth", out_col="dt_local"):
    """Convert naive UTC column to timezone-aware local time."""
    if df.empty or col not in df.columns:
        return df.assign(**{out_col: pd.NaT})
    tz = pytz.timezone(tz_name)
    return df.assign(**{out_col: pd.to_datetime(df[col]).dt.tz_localize(pytz.UTC).dt.tz_convert(tz)})


def build_motion_windows(occ_local: pd.DataFrame) -> pd.DataFrame:
    """
    Build one row per motion ON interval.
    Columns: id, start_local, end_local, duration_s
    """
    if occ_local.empty or "motionDetected" not in occ_local.columns:
        return pd.DataFrame(columns=["id", "start_local", "end_local", "duration_s"])

    df = occ_local.copy()
    df["motionDetected"] = df["motionDetected"].fillna(False).astype(bool)
    df = df.sort_values(["id", "dt_local"])

    windows = []
    for sid, grp in df.groupby("id", sort=False):
        g = grp[["dt_local", "motionDetected"]].copy()
        g["prev"] = g["motionDetected"].shift(fill_value=False)

        rises = g[(g["motionDetected"] == True) & (g["prev"] == False)]["dt_local"].tolist()
        falls = g[(g["motionDetected"] == False) & (g["prev"] == True)]["dt_local"].tolist()

        i = 0
        j = 0
        while i < len(rises):
            start = rises[i]
            if j < len(falls) and falls[j] > start:
                end = falls[j]
                j += 1
            else:
                end = g["dt_local"].max()
            windows.append(
                {
                    "id": sid,
                    "start_local": start,
                    "end_local": end,
                    "duration_s": (end - start).total_seconds(),
                }
            )
            i += 1

    return pd.DataFrame(windows)


def plot_combined_timeline(occ_local: pd.DataFrame, garage_local: pd.DataFrame, out_png: Path, tz_name: str):
    """
    Plot motion ON/OFF edges and garage states in one figure with shared x-axis.
    """
    if occ_local.empty and garage_local.empty:
        print("[WARN] No motion or garage data to plot.")
        return

    tz = pytz.timezone(tz_name)
    fig, (ax_motion, ax_garage) = plt.subplots(
        2, 1, figsize=(14, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )

    # Motion ON/OFF edges (same style as motion_edge_shapes)
    if occ_local.empty or "motionDetected" not in occ_local.columns:
        ax_motion.text(0.5, 0.5, "No motion data", transform=ax_motion.transAxes, ha="center", va="center")
        ax_motion.set_yticks([])
    else:
        df = occ_local.copy()
        df["dt_local"] = pd.to_datetime(df["dt_local"], errors="coerce")
        if getattr(df["dt_local"].dt, "tz", None) is None:
            df["dt_local"] = df["dt_local"].dt.tz_localize("UTC").dt.tz_convert(tz)
        else:
            df["dt_local"] = df["dt_local"].dt.tz_convert(tz)

        df["motionDetected"] = df["motionDetected"].fillna(False).astype(bool)
        df = df.sort_values(["id", "dt_local"])
        df["prev"] = df.groupby("id")["motionDetected"].shift(fill_value=False)

        rises = df[(df["motionDetected"] == True) & (df["prev"] == False)]
        falls = df[(df["motionDetected"] == False) & (df["prev"] == True)]

        sensor_ids = list(df["id"].drop_duplicates())
        y_map = {sid: idx for idx, sid in enumerate(sensor_ids)}

        for sid, grp in rises.groupby("id"):
            ax_motion.scatter(
                grp["dt_local"],
                [y_map[sid]] * len(grp),
                s=40,
                marker="o",
                color="#2e7d32",
                label=f"{sid} ON",
            )
        for sid, grp in falls.groupby("id"):
            ax_motion.scatter(
                grp["dt_local"],
                [y_map[sid]] * len(grp),
                s=50,
                marker="x",
                color="#c62828",
                label=f"{sid} OFF",
            )

        ax_motion.set_yticks(list(y_map.values()))
        ax_motion.set_yticklabels(sensor_ids)
        ax_motion.set_ylabel("Motion Sensor")
        ax_motion.grid(True, linestyle="--", alpha=0.4)
        ax_motion.legend(loc="upper left", fontsize="small")

    # Garage open/closed dot plot
    if garage_local.empty or "state" not in garage_local.columns:
        ax_garage.text(0.5, 0.5, "No garage state data", transform=ax_garage.transAxes, ha="center", va="center")
        ax_garage.set_yticks([])
    else:
        df = garage_local.copy().sort_values(["id", "dt_local"])
        df["state"] = df["state"].astype(str).str.lower()

        for sid, grp in df.groupby("id"):
            open_pts = grp[grp["state"] == "open"]
            closed_pts = grp[grp["state"] == "closed"]

            if not open_pts.empty:
                ax_garage.scatter(
                    open_pts["dt_local"],
                    [1] * len(open_pts),
                    s=28,
                    marker="o",
                    color="#ef6c00",
                    label=f"{sid} open",
                )
            if not closed_pts.empty:
                ax_garage.scatter(
                    closed_pts["dt_local"],
                    [0] * len(closed_pts),
                    s=28,
                    marker="o",
                    color="#1565c0",
                    label=f"{sid} closed",
                )

        ax_garage.set_yticks([0, 1])
        ax_garage.set_yticklabels(["closed", "open"])
        ax_garage.set_ylabel("Garage State")
        ax_garage.grid(True, linestyle="--", alpha=0.4)
        ax_garage.legend(loc="upper left", fontsize="small")

    ax_garage.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=tz))
    plt.xticks(rotation=45, ha="right")
    ax_motion.set_title("Motion ON/OFF + Garage Timeline (shared time scale)")
    ax_garage.set_xlabel(f"Local Time ({tz_name})")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"[INFO] Saved combined timeline → {out_png}")


def process_one_log(log_file: Path, tz_name: str, output_dir: Path | None):
    if not log_file.exists():
        print(f"[WARN] Missing file: {log_file}")
        return

    outdir = output_dir if output_dir else log_file.parent
    outdir.mkdir(parents=True, exist_ok=True)
    base = outdir / log_file.stem

    print(f"[INFO] Parsing {log_file.name} ...")
    occ_df, garage_df = parse_motion_and_garage(log_file)

    occ_local = localize(occ_df, "dt_utc", tz_name, "dt_local")
    garage_local = localize(garage_df, "dt_utc", tz_name, "dt_local")
    motion_windows = build_motion_windows(occ_local)

    # CSV exports
    motion_csv = base.with_name(f"{base.stem}_motion_windows.csv")
    garage_csv = base.with_name(f"{base.stem}_garage_states.csv")
    motion_windows.to_csv(motion_csv, index=False, encoding="utf-8")
    garage_local.to_csv(garage_csv, index=False, encoding="utf-8")
    print(f"[INFO] Saved CSVs → {motion_csv.name}, {garage_csv.name}")

    # Combined timeline plot
    out_png = base.with_name(f"{base.stem}_motion_garage_timeline.png")
    plot_combined_timeline(occ_local, garage_local, out_png, tz_name)


def main():
    ap = argparse.ArgumentParser(
        description="Extract and plot motion intervals + garage door states on a shared time axis."
    )
    ap.add_argument("logs", nargs="+", help="Path(s) to .log/.txt files")
    ap.add_argument("--tz", default="Australia/Perth", help="IANA timezone (default: Australia/Perth)")
    ap.add_argument(
        "--outdir",
        default=None,
        help="Optional output folder. Default: same folder as each input log",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir) if args.outdir else None
    for log_path in args.logs:
        process_one_log(Path(log_path), args.tz, outdir)


if __name__ == "__main__":
    main()

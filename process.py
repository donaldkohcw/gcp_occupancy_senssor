#!/usr/bin/env python3
"""
adi_log_plot.py — parse Advantage Air JSON-line logs and plot/save summaries.

Features
- Parses JSON lines with sections: occupancySensors, temperatureSensors, zones, garageDoors, aircons
- Converts UTC timestamps to a local timezone (default Australia/Perth)
- Exports CSV summaries (./out/<basename>_*.csv)
- Plots:
  - Motion events timeline per occupancy sensor
  - Temperature readings per temperature sensor
  - Zone target % & temp sensor values
  - Garage door state transitions

Usage
  python adi_log_plot.py 6Nov_Adi.log [6Nov_Joey.log ...]
  python adi_log_plot.py file.log --plots motion temp zones garage --tz Australia/Perth
"""

import argparse
import json
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import pytz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

LINE_STYLE = {
    "linestyle": "-",
    "linewidth": 1.6,
    "marker": "o",
    "markersize": 3.0,
}


# --------- Helpers ---------
def safe_json_from_line(line: str):
    """Extract trailing JSON object from a line; return dict or None."""
    m = re.search(r'\{.*\}$', line.strip())
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

def localize(df, col="dt_utc", tz_name="Australia/Perth", out_col="dt_local"):
    """Convert naive UTC column to timezone-aware local time."""
    if df.empty or col not in df.columns:
        return df.assign(**{out_col: pd.NaT})
    tz = pytz.timezone(tz_name)
    return df.assign(**{out_col: pd.to_datetime(df[col]).dt.tz_localize(pytz.UTC).dt.tz_convert(tz)})

def ensure_outdir():
    p = Path("./out")
    p.mkdir(parents=True, exist_ok=True)
    return p

# --------- Parsing ---------
def parse_log(path: Path):
    """
    Return dict of DataFrames:
      occ_df:  occupancySensors rows (dt_utc, id, motionDetected, temperature, humidity, batteryLevel, ...)
      ts_df:   temperatureSensors rows (dt_utc, id, temperature)
      zones_df: zones rows (dt_utc, id, targetPercentCool, targetPercentHeat, temperatureSensorValue)
      garage_df: garageDoors rows (dt_utc, id, state, sensorState, lastMovedEpoc)
      ac_df:   aircons rows (dt_utc, id, actualTemperature, mode, etc. if present)
    """
    occ_rows, ts_rows, zones_rows, garage_rows, ac_rows = [], [], [], [], []

    text = path.read_text(encoding="utf-8", errors="ignore")
    for ln in text.splitlines():
        obj = safe_json_from_line(ln)
        if not obj:
            continue

        ts = parse_timestamp_utc(obj.get("id", ""))
        if ts is None:
            continue

        # occupancySensors
        occ = obj.get("occupancySensors")
        if isinstance(occ, dict):
            for sid, payload in occ.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        if k != "id":
                            row[k] = v
                occ_rows.append(row)

        # temperatureSensors
        tss = obj.get("temperatureSensors")
        if isinstance(tss, dict):
            for sid, payload in tss.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        if k != "id":
                            row[k] = v
                ts_rows.append(row)

        # zones
        zs = obj.get("zones")
        if isinstance(zs, dict):
            for sid, payload in zs.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        if k != "id":
                            row[k] = v
                zones_rows.append(row)

        # garageDoors
        gd = obj.get("garageDoors")
        if isinstance(gd, dict):
            for sid, payload in gd.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        if k != "id":
                            row[k] = v
                garage_rows.append(row)

        # aircons (optional)
        ac = obj.get("aircons")
        if isinstance(ac, dict):
            for sid, payload in ac.items():
                row = {"dt_utc": ts, "id": sid}
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        if k != "id":
                            row[k] = v
                ac_rows.append(row)

    def mkdf(rows):
        return pd.DataFrame.from_records(rows) if rows else pd.DataFrame()

    return {
        "occ_df": mkdf(occ_rows),
        "ts_df": mkdf(ts_rows),
        "zones_df": mkdf(zones_rows),
        "garage_df": mkdf(garage_rows),
        "ac_df": mkdf(ac_rows),
    }

# --------- CSV Export ---------
def export_csvs(base_out: Path, dfs_local):
    for key, df in dfs_local.items():
        if df.empty:
            continue
        (base_out.with_name(f"{base_out.stem}_{key}.csv")).write_text(
            df.to_csv(index=False), encoding="utf-8"
        )


def export_occupancy_metric_csvs(base_out: Path, occ_local: pd.DataFrame):
    """Export occupancy sensor humidity and temperature into separate CSV files."""
    if occ_local.empty:
        return

    base_cols = [c for c in ["dt_utc", "dt_local", "id"] if c in occ_local.columns]

    if "humidity" in occ_local.columns:
        hum_cols = base_cols + ["humidity"]
        hum_df = occ_local[hum_cols].copy().sort_values(["id", "dt_local"] if "dt_local" in hum_cols else ["id"])
        (base_out.with_name(f"{base_out.stem}_occupancy_humidity.csv")).write_text(
            hum_df.to_csv(index=False), encoding="utf-8"
        )

    if "temperature" in occ_local.columns:
        temp_cols = base_cols + ["temperature"]
        temp_df = occ_local[temp_cols].copy().sort_values(["id", "dt_local"] if "dt_local" in temp_cols else ["id"])
        (base_out.with_name(f"{base_out.stem}_occupancy_temperature.csv")).write_text(
            temp_df.to_csv(index=False), encoding="utf-8"
        )

# --------- Plots ---------
def plot_motion(occ_local: pd.DataFrame, outpath: Path, title_prefix: str, tz_name: str = "Australia/Perth"):
    """Plot rising (ON) and falling (OFF) motion edges with local-time axis."""
    if occ_local.empty or "motionDetected" not in occ_local.columns:
        return

    import matplotlib.dates as mdates
    import pytz
    wa_tz = pytz.timezone(tz_name)

    df = occ_local.copy()

    # --- Force dt_local to be timezone-aware in Perth ---
    # If dt_local has lost tz info (naive), treat as UTC then convert to Perth.
    df["dt_local"] = pd.to_datetime(df["dt_local"], errors="coerce")
    if getattr(df["dt_local"].dt, "tz", None) is None:
        df["dt_local"] = df["dt_local"].dt.tz_localize("UTC").dt.tz_convert(wa_tz)
    else:
        df["dt_local"] = df["dt_local"].dt.tz_convert(wa_tz)
    # -----------------------------------------------------

    df["motionDetected"] = df["motionDetected"].fillna(False).astype(bool)
    df = df.sort_values(["id", "dt_local"])
    df["prev"] = df.groupby("id")["motionDetected"].shift(fill_value=False)

    rises = df[(df["motionDetected"] == True)  & (df["prev"] == False)]
    falls = df[(df["motionDetected"] == False) & (df["prev"] == True)]

    plt.figure(figsize=(12, 6))

    # Rising edges: green circles
    for sid, grp in rises.groupby("id"):
        plt.scatter(grp["dt_local"], [sid]*len(grp), s=40, marker="o", label=f"{sid} ON")

    # Falling edges: red crosses
    for sid, grp in falls.groupby("id"):
        plt.scatter(grp["dt_local"], [sid]*len(grp), s=50, marker="x", label=f"{sid} OFF")

    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=wa_tz))  # date + AM/PM
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Time (local)")
    plt.ylabel("Sensor ID")
    plt.title(f"{title_prefix} — Motion ON/OFF Events (local time)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.tight_layout()

    png = outpath.with_name(f"{outpath.stem}_motion_edges_shapes.png")
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"[INFO] Saved ON/OFF edge plot (Perth time) → {png}")


def plot_temps(ts_local: pd.DataFrame, outpath: Path, title_prefix: str, tz_name: str = "Australia/Perth"):
    if ts_local.empty or "temperature" not in ts_local.columns:
        return
    wa_tz = pytz.timezone(tz_name)
    df = ts_local.copy()
    df["dt_local"] = pd.to_datetime(df["dt_local"], errors="coerce")
    if getattr(df["dt_local"].dt, "tz", None) is None:
        df["dt_local"] = df["dt_local"].dt.tz_localize("UTC").dt.tz_convert(wa_tz)
    else:
        df["dt_local"] = df["dt_local"].dt.tz_convert(wa_tz)

    plt.figure(figsize=(12, 6))
    for sid, grp in df.groupby("id"):
        grp = grp.sort_values("dt_local")
        plt.plot(grp["dt_local"], grp["temperature"], label=sid, **LINE_STYLE)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=wa_tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Time (local)")
    plt.ylabel("Temperature (°C)")
    plt.title(f"{title_prefix} — Temperature Sensors")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    png = outpath.with_name(f"{outpath.stem}_temps.png")
    plt.savefig(png, dpi=150)
    plt.close()

def plot_zones(z_local: pd.DataFrame, outpath: Path, title_prefix: str, tz_name: str = "Australia/Perth"):
    if z_local.empty:
        return
    wa_tz = pytz.timezone(tz_name)
    df = z_local.copy()
    df["dt_local"] = pd.to_datetime(df["dt_local"], errors="coerce")
    if getattr(df["dt_local"].dt, "tz", None) is None:
        df["dt_local"] = df["dt_local"].dt.tz_localize("UTC").dt.tz_convert(wa_tz)
    else:
        df["dt_local"] = df["dt_local"].dt.tz_convert(wa_tz)

    plt.figure(figsize=(12, 6))
    for sid, grp in df.groupby("id"):
        grp = grp.sort_values("dt_local")
        if "temperatureSensorValue" in grp.columns:
            plt.plot(grp["dt_local"], grp["temperatureSensorValue"], label=f"{sid} tempVal", **LINE_STYLE)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=wa_tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Time (local)")
    plt.ylabel("Zone Temp (°C)")
    plt.title(f"{title_prefix} — Zone temperatureSensorValue")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    png = outpath.with_name(f"{outpath.stem}_zones.png")
    plt.savefig(png, dpi=150)
    plt.close()


def plot_occupancy_humidity(occ_local: pd.DataFrame, outpath: Path, title_prefix: str, tz_name: str = "Australia/Perth"):
    if occ_local.empty or "humidity" not in occ_local.columns:
        return
    wa_tz = pytz.timezone(tz_name)
    df = occ_local.copy()
    df["dt_local"] = pd.to_datetime(df["dt_local"], errors="coerce")
    if getattr(df["dt_local"].dt, "tz", None) is None:
        df["dt_local"] = df["dt_local"].dt.tz_localize("UTC").dt.tz_convert(wa_tz)
    else:
        df["dt_local"] = df["dt_local"].dt.tz_convert(wa_tz)

    plt.figure(figsize=(12, 6))
    for sid, grp in df.groupby("id"):
        grp = grp.sort_values("dt_local")
        plt.plot(grp["dt_local"], grp["humidity"], label=sid, **LINE_STYLE)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=wa_tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Time (local)")
    plt.ylabel("Humidity (%)")
    plt.title(f"{title_prefix} — Occupancy Sensor Humidity")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    png = outpath.with_name(f"{outpath.stem}_occupancy_humidity.png")
    plt.savefig(png, dpi=150)
    plt.close()


def plot_occupancy_temperature(occ_local: pd.DataFrame, outpath: Path, title_prefix: str, tz_name: str = "Australia/Perth"):
    if occ_local.empty or "temperature" not in occ_local.columns:
        return
    wa_tz = pytz.timezone(tz_name)
    df = occ_local.copy()
    df["dt_local"] = pd.to_datetime(df["dt_local"], errors="coerce")
    if getattr(df["dt_local"].dt, "tz", None) is None:
        df["dt_local"] = df["dt_local"].dt.tz_localize("UTC").dt.tz_convert(wa_tz)
    else:
        df["dt_local"] = df["dt_local"].dt.tz_convert(wa_tz)

    plt.figure(figsize=(12, 6))
    for sid, grp in df.groupby("id"):
        grp = grp.sort_values("dt_local")
        plt.plot(grp["dt_local"], grp["temperature"], label=sid, **LINE_STYLE)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=wa_tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Time (local)")
    plt.ylabel("Temperature (°C)")
    plt.title(f"{title_prefix} — Occupancy Sensor Temperature")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    png = outpath.with_name(f"{outpath.stem}_occupancy_temperature.png")
    plt.savefig(png, dpi=150)
    plt.close()

def plot_garage(garage_local: pd.DataFrame, outpath: Path, title_prefix: str):
    if garage_local.empty or "state" not in garage_local.columns:
        return
    # map states to integers for plotting
    state_map = {None: 0, "notKnown": 0, "closed": 1, "moving": 2, "open": 3}
    df = garage_local.copy()
    df["state_num"] = df["state"].map(state_map).fillna(0)

    plt.figure(figsize=(12, 6))
    for sid, grp in df.groupby("id"):
        grp = grp.sort_values("dt_local")
        plt.step(grp["dt_local"], grp["state_num"], where="post", label=sid)
    plt.xlabel("Time (local)")
    plt.ylabel("State (0=unknown,1=closed,2=moving,3=open)")
    plt.title(f"{title_prefix} — Garage Door State")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    png = outpath.with_name(f"{outpath.stem}_garage.png")
    plt.savefig(png, dpi=150)
    plt.close()

def build_motion_windows(occ_local: pd.DataFrame) -> pd.DataFrame:
    """
    From occupancy rows with motionDetected booleans, return one row per
    ON interval: [start_local, end_local] per sensor id, plus duration_s.
    If a motion stays ON to the end of the log, we close the window at the
    last timestamp seen for that sensor.
    """
    if occ_local.empty or "motionDetected" not in occ_local.columns:
        return pd.DataFrame(columns=["id","start_local","end_local","duration_s"])

    df = occ_local.copy()
    df["motionDetected"] = df["motionDetected"].fillna(False).astype(bool)
    df = df.sort_values(["id", "dt_local"])

    windows = []
    for sid, grp in df.groupby("id", sort=False):
        g = grp[["dt_local","motionDetected"]].copy()
        g["prev"] = g["motionDetected"].shift(fill_value=False)

        # Rising (False->True) and Falling (True->False)
        rises   = g[(g["motionDetected"] == True)  & (g["prev"] == False)]["dt_local"].tolist()
        falls   = g[(g["motionDetected"] == False) & (g["prev"] == True)]["dt_local"].tolist()

        # Pair them: each rise closes at the next fall (if present)
        i = j = 0
        while i < len(rises):
            start = rises[i]
            if j < len(falls) and falls[j] > start:
                end = falls[j]
                j += 1
            else:
                # No falling edge after this start → close at last sample for this sensor
                end = g["dt_local"].max()
            duration_s = (end - start).total_seconds()
            windows.append({"id": sid, "start_local": start, "end_local": end, "duration_s": duration_s})
            i += 1

    return pd.DataFrame(windows)


def plot_motion_windows(windows_df: pd.DataFrame, outpath: Path, title_prefix: str):
    """Plot ON windows as horizontal bars per sensor (Gantt-like)."""
    if windows_df.empty:
        print(f"[WARN] No motion windows to plot for {title_prefix}")
        return

    import matplotlib.dates as mdates, pytz
    wa_tz = pytz.timezone("Australia/Perth")

    # --- force timezone awareness ---
    windows_df = windows_df.copy()
    for col in ["start_local", "end_local"]:
        if col in windows_df.columns:
            windows_df[col] = pd.to_datetime(windows_df[col], utc=True).dt.tz_convert(wa_tz)
    # ---------------------------------

    sensor_ids = list(windows_df["id"].drop_duplicates())
    y_map = {sid: idx for idx, sid in enumerate(sensor_ids)}

    plt.figure(figsize=(12, 6))
    ax = plt.gca()

    # Draw bars
    for _, row in windows_df.iterrows():
        y = y_map[row["id"]]
        ax.hlines(y=y, xmin=row["start_local"], xmax=row["end_local"], linewidth=6)

    # X-axis formatting with date + AM/PM
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=wa_tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Time (local)")
    plt.ylabel("Sensor ID")
    plt.title(f"{title_prefix} — Occupancy Windows (ON intervals)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    png = outpath.with_name(f"{outpath.stem}_motion_windows.png")
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"[INFO] Saved motion-window plot → {png}")


# --------- Main ---------
def main():
    ap = argparse.ArgumentParser(description="Parse Advantage Air logs and plot results.")
    ap.add_argument("logs", nargs="+", help="Path(s) to .log files (JSON lines).")
    ap.add_argument("--tz", default="Australia/Perth", help="IANA timezone (default: Australia/Perth)")
    ap.add_argument("--plots", nargs="*", default=["motion", "temp", "zones", "garage", "occ_humidity", "occ_temp"],
                    choices=["motion", "temp", "zones", "garage", "occ_humidity", "occ_temp"],
                    help="Which plots to render.")
    args = ap.parse_args()


    for log_path in args.logs:
        p = Path(log_path)

        # Save outputs in the same folder as the log file
        outdir = p.parent

        if not p.exists():
            print(f"[WARN] Missing file: {p}")
            continue

        print(f"[INFO] Parsing {p.name} ...")
        dfs = parse_log(p)

        # Localize times
        occ_local    = localize(dfs["occ_df"],    "dt_utc", args.tz, "dt_local")
        ts_local     = localize(dfs["ts_df"],     "dt_utc", args.tz, "dt_local")
        zones_local  = localize(dfs["zones_df"],  "dt_utc", args.tz, "dt_local")
        garage_local = localize(dfs["garage_df"], "dt_utc", args.tz, "dt_local")
        ac_local     = localize(dfs["ac_df"],     "dt_utc", args.tz, "dt_local")

        # Save CSVs
        base = outdir / p.stem

        export_csvs(base, {
            "occupancy": occ_local,
            "temps": ts_local,
            "zones": zones_local,
            "garage": garage_local,
            "aircons": ac_local,
        })
        export_occupancy_metric_csvs(base, occ_local)
        print(f"[INFO] CSVs written to: {outdir.resolve()}")

        # ===== NEW: build + save + plot occupancy ON windows =====
        try:
            motion_windows = build_motion_windows(occ_local)
            (base.with_name(f"{base.stem}_motion_windows.csv")).write_text(
                motion_windows.to_csv(index=False), encoding="utf-8"
            )
            plot_motion_windows(motion_windows, base, p.stem)
        except Exception as e:
            print(f"[WARN] Motion windows step skipped due to error: {e}")
        # =========================================================

        # Plots
        title_prefix = p.stem
        if "motion" in args.plots:
            plot_motion(occ_local, base, title_prefix, args.tz)
        if "temp" in args.plots:
            plot_temps(ts_local, base, title_prefix, args.tz)
        if "zones" in args.plots:
            plot_zones(zones_local, base, title_prefix, args.tz)
        if "garage" in args.plots:
            plot_garage(garage_local, base, title_prefix)
        if "occ_humidity" in args.plots:
            plot_occupancy_humidity(occ_local, base, title_prefix, args.tz)
        if "occ_temp" in args.plots:
            plot_occupancy_temperature(occ_local, base, title_prefix, args.tz)
        print(f"[INFO] Plots saved (if data present) to: {outdir.resolve()}")

        # Quick console summary
        def summarize(df, name):
            if df.empty:
                print(f"  - {name}: no rows")
                return
            print(f"  - {name}: {len(df)} rows; window {df['dt_local'].min()} → {df['dt_local'].max()}; ids={df['id'].nunique()}")

        print("[INFO] Summary")
        summarize(occ_local, "occupancy")
        summarize(ts_local, "temps")
        summarize(zones_local, "zones")
        summarize(garage_local, "garage")
        summarize(ac_local, "aircons")

if __name__ == "__main__":
    main()


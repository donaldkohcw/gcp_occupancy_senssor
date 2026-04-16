#!/usr/bin/env python3
"""
extract_battery_level.py

Extract batteryLevel readings from Advantage Air JSON-line logs.

Usage:
  python extract_battery_level.py file.log [file2.log ...]
  python extract_battery_level.py file.log --tz Australia/Perth --plot
"""

import argparse
import glob
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import pytz


def safe_json_from_line(line: str):
    m = re.search(r"\{.*\}$", line.strip())
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def parse_timestamp_utc(ts: str):
    for fmt in ("%Y/%m/%d %H:%M:%S,%f", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            pass
    return None


def localize(df, tz_name="Australia/Perth"):
    if df.empty:
        return df.assign(dt_local=pd.NaT)
    tz = pytz.timezone(tz_name)
    return df.assign(
        dt_local=pd.to_datetime(df["dt_utc"]).dt.tz_localize(pytz.UTC).dt.tz_convert(tz)
    )


def extract_battery_rows(path: Path):
    rows = []
    text = path.read_text(encoding="utf-8", errors="ignore")

    sections = [
        "occupancySensors",
        "temperatureSensors",
        "garageDoors",
        "zones",
        "aircons",
    ]

    for ln in text.splitlines():
        obj = safe_json_from_line(ln)
        if not obj:
            continue

        ts = parse_timestamp_utc(obj.get("id", ""))
        if ts is None:
            continue

        for section in sections:
            block = obj.get(section)
            if not isinstance(block, dict):
                continue

            for sid, payload in block.items():
                if not isinstance(payload, dict):
                    continue
                if "batteryLevel" not in payload:
                    continue
                rows.append(
                    {
                        "dt_utc": ts,
                        "section": section,
                        "id": sid,
                        "batteryLevel": payload.get("batteryLevel"),
                    }
                )

    return pd.DataFrame.from_records(rows) if rows else pd.DataFrame(
        columns=["dt_utc", "section", "id", "batteryLevel"]
    )


def plot_battery(df_local: pd.DataFrame, out_png: Path, tz_name: str):
    if df_local.empty:
        print("[WARN] No batteryLevel rows to plot.")
        return

    plt.figure(figsize=(12, 6))
    for key, grp in df_local.groupby(["section", "id"], sort=False):
        label = f"{key[0]}:{key[1]}"
        g = grp.sort_values("dt_local")
        plt.plot(g["dt_local"], g["batteryLevel"], marker="o", linestyle="-", linewidth=1, markersize=3, label=label)

    tz = pytz.timezone(tz_name)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel(f"Local Time ({tz_name})")
    plt.ylabel("batteryLevel")
    plt.title("Battery Level Over Time")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"[INFO] Saved battery plot -> {out_png}")


def process_one(log_file: Path, tz_name: str, outdir: Path | None, do_plot: bool):
    if not log_file.exists():
        print(f"[WARN] Missing file: {log_file}")
        return

    target_dir = outdir if outdir else log_file.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    base = target_dir / log_file.stem

    print(f"[INFO] Extracting batteryLevel from {log_file.name} ...")
    df = extract_battery_rows(log_file)
    df_local = localize(df, tz_name)

    out_csv = base.with_name(f"{base.stem}_battery_levels.csv")
    df_local.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"[INFO] Saved CSV -> {out_csv}")

    if do_plot:
        out_png = base.with_name(f"{base.stem}_battery_levels.png")
        plot_battery(df_local, out_png, tz_name)

    print(f"[INFO] Rows extracted: {len(df_local)}")


def main():
    ap = argparse.ArgumentParser(description="Extract batteryLevel rows from Advantage Air logs.")
    ap.add_argument("logs", nargs="+", help="Path(s) to .log/.txt files")
    ap.add_argument("--tz", default="Australia/Perth", help="IANA timezone (default: Australia/Perth)")
    ap.add_argument("--outdir", default=None, help="Optional output folder")
    ap.add_argument("--plot", action="store_true", help="Generate battery level plot PNG")
    args = ap.parse_args()

    outdir = Path(args.outdir) if args.outdir else None

    expanded_logs: list[Path] = []
    for log in args.logs:
        matches = [Path(p) for p in glob.glob(log)]
        if matches:
            expanded_logs.extend(matches)
        else:
            expanded_logs.append(Path(log))

    # Keep order stable while removing duplicates.
    seen = set()
    ordered_logs: list[Path] = []
    for p in expanded_logs:
        k = str(p.resolve()) if p.exists() else str(p)
        if k in seen:
            continue
        seen.add(k)
        ordered_logs.append(p)

    for log in ordered_logs:
        process_one(log, args.tz, outdir, args.plot)


if __name__ == "__main__":
    main()

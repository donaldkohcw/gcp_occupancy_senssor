#!/usr/bin/env python3
"""
Extract battery levels for device 276 from all .txt logs in a folder
and plot battery voltage over time.

Default source folder:
  X:\\R&D\\STAFF FOLDERS\\DonaldK\\Sensor_logs\\Adi\\

Usage:
  python extract_device_276_voltage.py
  python extract_device_276_voltage.py --folder "X:\\R&D\\...\\Adi" --device 276
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


DEFAULT_FOLDER = r"X:\R&D\STAFF FOLDERS\DonaldK\Sensor_logs\Adi"
DEFAULT_DEVICE = "276"
DEFAULT_TZ = "Australia/Perth"


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


def battery_to_voltage(val):
    """
    Convert batteryLevel to actual voltage:
      voltage = (batteryLevel / 255) * 5
    """
    if val is None:
        return None
    try:
        x = float(val)
    except Exception:
        return None
    return (x / 255.0) * 5.0


def extract_from_file(file_path: Path, device_id: str):
    rows = []
    sections = ["occupancySensors", "temperatureSensors", "garageDoors", "zones", "aircons"]
    text = file_path.read_text(encoding="utf-8", errors="ignore")

    for ln in text.splitlines():
        obj = safe_json_from_line(ln)
        if not obj:
            continue

        dt_utc = parse_timestamp_utc(obj.get("id", ""))
        if dt_utc is None:
            continue

        for section in sections:
            block = obj.get(section)
            if not isinstance(block, dict):
                continue

            payload = block.get(device_id)
            if not isinstance(payload, dict):
                continue
            if "batteryLevel" not in payload:
                continue

            raw_level = payload.get("batteryLevel")
            rows.append(
                {
                    "file": file_path.name,
                    "dt_utc": dt_utc,
                    "section": section,
                    "device_id": device_id,
                    "batteryLevel": raw_level,
                    "voltage_v": battery_to_voltage(raw_level),
                }
            )

    return rows


def main():
    ap = argparse.ArgumentParser(
        description="Extract battery levels for one device across all .txt files and plot voltage."
    )
    ap.add_argument("--folder", default=DEFAULT_FOLDER, help="Folder containing .txt log files")
    ap.add_argument("--device", default=DEFAULT_DEVICE, help="Device id to extract (default: 276)")
    ap.add_argument("--tz", default=DEFAULT_TZ, help="Timezone for plotting and CSV dt_local")
    ap.add_argument("--outdir", default=None, help="Output folder (default: same as --folder)")
    args = ap.parse_args()

    src = Path(args.folder)
    if not src.exists():
        raise SystemExit(f"[ERROR] Folder not found: {src}")

    txt_files = sorted(src.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"[ERROR] No .txt files found in: {src}")

    all_rows = []
    for fp in txt_files:
        all_rows.extend(extract_from_file(fp, str(args.device)))

    if not all_rows:
        raise SystemExit(f"[ERROR] No batteryLevel data found for device {args.device} in {len(txt_files)} files.")

    df = pd.DataFrame(all_rows).sort_values("dt_utc")
    tz = pytz.timezone(args.tz)
    df["dt_local"] = pd.to_datetime(df["dt_utc"]).dt.tz_localize(pytz.UTC).dt.tz_convert(tz)

    outdir = Path(args.outdir) if args.outdir else src
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / f"device_{args.device}_battery_voltage.csv"
    png_path = outdir / f"device_{args.device}_battery_voltage.png"

    df.to_csv(csv_path, index=False, encoding="utf-8")

    plt.figure(figsize=(12, 6))
    plt.plot(df["dt_local"], df["voltage_v"], marker="o", linestyle="-", linewidth=1.2, markersize=3.5)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %I:%M %p", tz=tz))
    plt.xticks(rotation=45, ha="right")
    plt.xlabel(f"Time ({args.tz})")
    plt.ylabel("Battery Voltage (V)")
    plt.title(f"Device {args.device} Battery Voltage")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()

    print(f"[INFO] Files scanned: {len(txt_files)}")
    print(f"[INFO] Rows extracted: {len(df)}")
    print(f"[INFO] CSV saved: {csv_path}")
    print(f"[INFO] Plot saved: {png_path}")


if __name__ == "__main__":
    main()

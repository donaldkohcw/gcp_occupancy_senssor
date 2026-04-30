#!/usr/bin/env python3
r"""
Run process.py for all configured users for a given folder number.

Usage:
  python .\run_process_all_users.py --20560

This maps folder number -> day label using the same base mapping as combine_daily.py,
then builds file paths like:
  X:\R&D\STAFF FOLDERS\DonaldK\Sensor_logs\<User>\<DayLabel>_<User>.txt
and calls process.py with all existing files.
"""

import datetime
import re
import subprocess
import sys
from pathlib import Path


USERS = ["Marg", "Joey", "Adi", "Owain", "Workroom"]
SENSOR_LOGS_BASE = Path(r"X:\R&D\STAFF FOLDERS\DonaldK\Sensor_logs")
BASE_FOLDER_NUM = 20402
BASE_DATE = datetime.date(2025, 11, 10)


def parse_folder_arg(argv: list[str]) -> int:
    folder_flags = [a for a in argv if re.fullmatch(r"--\d+", a)]
    if not folder_flags:
        raise ValueError("Missing folder argument. Example: --20560")
    if len(folder_flags) > 1:
        raise ValueError(f"Expected one folder argument, got: {', '.join(folder_flags)}")
    return int(folder_flags[0][2:])


def day_label_from_folder(folder_num: int) -> str:
    target_date = BASE_DATE + datetime.timedelta(days=(folder_num - BASE_FOLDER_NUM))
    return target_date.strftime("%d%b")


def main() -> int:
    try:
        folder_num = parse_folder_arg(sys.argv[1:])
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        print("Usage: python .\\run_process_all_users.py --20560")
        return 2

    day_label = day_label_from_folder(folder_num)
    logs: list[str] = []

    for user in USERS:
        p = SENSOR_LOGS_BASE / user / f"{day_label}_{user}.txt"
        if p.exists():
            logs.append(str(p))
        else:
            print(f"[WARN] Missing: {p}")

    if not logs:
        print(f"[ERROR] No input files found for folder {folder_num} ({day_label}).")
        return 1

    cmd = [sys.executable, str(Path(__file__).with_name("process.py"))] + logs
    print(f"[INFO] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())


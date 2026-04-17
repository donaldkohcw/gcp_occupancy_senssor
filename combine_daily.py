import argparse
import datetime
import os
import subprocess
from zoneinfo import ZoneInfo

# === CONFIG ===
BUCKET = "aaai_bucket"
IDS = {
    "Marg": "3hXTzsJwgUkKcNHeHLrFYy",
    "Joey": "azmZYQDnLWC6DwGnuzEABg",
    "Adi": "Ghaaki8CbZvcZzvZFFRwu8",
    "Owain": "hwvhMAKawhLYaGByEXBVPs",
    "Workroom": "6AsvkRLNW4TsD5WrpKX2Z5",
}

#  Use UNC paths — no drive mapping
LOCAL_BASE = r"\\adair-file2\RnD\RDrive\R&D\STAFF FOLDERS\DonaldK\Sensor_logs\all"
OUTPUT_BASE = r"\\adair-file2\RnD\RDrive\R&D\STAFF FOLDERS\DonaldK\Sensor_logs"
LOCAL_TZ = "Australia/Perth"


# === STEP 1: Map date -> folder number ===
def get_folder_number_for_date(target_date):
    base_folder = 20402
    base_date = datetime.date(2025, 11, 10)

    day_offset = (target_date - base_date).days
    folder_number = base_folder + day_offset

    # e.g., "10Nov"
    day_label = target_date.strftime("%d%b")
    return str(folder_number), day_label


def get_date_for_folder_number(folder_number):
    base_folder = 20402
    base_date = datetime.date(2025, 11, 10)
    day_offset = int(folder_number) - base_folder
    return base_date + datetime.timedelta(days=day_offset)


def get_target_days():
    today = datetime.datetime.now(ZoneInfo(LOCAL_TZ)).date()
    yesterday = today - datetime.timedelta(days=1)
    # Process both days in one run.
    return [yesterday, today]


def parse_args():
    parser = argparse.ArgumentParser(description="Download and combine occupancy logs.")
    parser.add_argument(
        "--folders",
        nargs="+",
        help="Optional explicit folder numbers to process, e.g. --folders 20559 20560",
    )
    return parser.parse_args()


# === STEP 2: High-speed download using gsutil ===
def download_gcs_folder(bucket_name, prefix, local_path):
    """Download from GCS with gsutil and fall back to gcloud storage cp."""
    os.makedirs(local_path, exist_ok=True)

    # Convert Windows backslashes to forward slashes for gsutil
    local_path_fixed = local_path.replace("\\", "/")

    src = f"gs://{bucket_name}/{prefix}"
    print(f"Requested copy: {src} -> \"{local_path_fixed}\"")

    commands = [
        (
            "gcloud storage(explicit)",
            [
                r"C:\Users\donaldk\google-cloud-sdk\bin\gcloud.cmd",
                "storage",
                "cp",
                "--recursive",
                src,
                local_path,
            ],
        ),
        (
            "gsutil(explicit)",
            [r"C:\Users\donaldk\google-cloud-sdk\bin\gsutil.cmd", "-m", "cp", "-r", src, local_path],
        ),
        ("gsutil(PATH)", ["gsutil", "-m", "cp", "-r", src, local_path]),
        ("gcloud storage", ["gcloud", "storage", "cp", "--recursive", src, local_path]),
    ]

    for label, cmd in commands:
        print(f"Running [{label}]: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except FileNotFoundError:
            print(f"{label} not found on PATH.")
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            stdout = (e.stdout or "").strip()
            details = stderr if stderr else stdout
            print(f"{label} failed for {prefix}: {details or str(e)}")

    return False


# === STEP 3: Combine all files ===
def combine_files(folder_path, output_file):
    """Concatenate all downloaded log files into one output file."""
    with open(output_file, "w", encoding="utf-8") as outfile:
        for root, _, files in os.walk(folder_path):
            for f in files:
                file_path = os.path.join(root, f)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as infile:
                    outfile.write(infile.read() + "\n")
    print(f"Combined logs saved to {output_file}")


def count_files(folder_path):
    total = 0
    for _, _, files in os.walk(folder_path):
        total += len(files)
    return total


# === STEP 4: Process each user ===
def process_user(name, folder_num, day_label):
    prefix = f"{IDS[name]}/{folder_num}/"
    local_path = os.path.join(LOCAL_BASE, f"{name}_{folder_num}")

    output_folder = os.path.join(OUTPUT_BASE, name)
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, f"{day_label}_{name}.txt")

    os.makedirs(local_path, exist_ok=True)
    os.makedirs(LOCAL_BASE, exist_ok=True)

    print(f"\n=== Processing {name} ===")
    print(f"GCS path: gs://{BUCKET}/{prefix}")

    success = download_gcs_folder(BUCKET, prefix, local_path)
    if success:
        file_count = count_files(local_path)
        if file_count == 0:
            print(f"No files downloaded for {name} ({day_label}) from {prefix}")
            return False
        combine_files(local_path, output_file)
        #shutil.rmtree(local_path)
        #print(f"Cleaned up temporary folder: {local_path}")
        return True
    else:
        print(f"Skipping {name} — no files found or gsutil failed.")
        return False


# === MAIN ===
def main():
    args = parse_args()
    day_failures = {}
    targets = []
    if args.folders:
        for folder_num in args.folders:
            target_day = get_date_for_folder_number(folder_num)
            day_label = target_day.strftime("%d%b")
            targets.append((str(folder_num), day_label))
        print(f"Target folders (manual): {', '.join(f'{d} (folder {f})' for f, d in targets)}")
    else:
        target_days = get_target_days()
        for d in target_days:
            folder_num, day_label = get_folder_number_for_date(d)
            targets.append((folder_num, day_label))
        print(f"Target days ({LOCAL_TZ}): {', '.join(f'{d} (folder {f})' for f, d in targets)}")

    for folder_num, day_label in targets:
        print(f"\n=== Starting log combine for {day_label} (folder {folder_num}) ===")

        failures = []
        for name in IDS:
            ok = process_user(name, folder_num, day_label)
            if not ok:
                failures.append(name)

        if failures:
            day_failures[day_label] = failures

    if day_failures:
        print("\nCompleted with failures:")
        for day_label, failures in day_failures.items():
            print(f"  {day_label}: {', '.join(failures)}")
    else:
        print("\nAll users processed successfully for yesterday and today.")


if __name__ == "__main__":
    main()

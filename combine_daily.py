import datetime
import os
import shutil
import subprocess

# === CONFIG ===
BUCKET = "aaai_bucket"
IDS = {
    "Joey": "azmZYQDnLWC6DwGnuzEABg",
    "Adi": "Ghaaki8CbZvcZzvZFFRwu8",
    "Owain": "hwvhMAKawhLYaGByEXBVPs",
    "Workroom": "6AsvkRLNW4TsD5WrpKX2Z5",
    "Marg": "3hXTzsJwgUkKcNHeHLrFYy",
}

#  Use UNC paths — no drive mapping
LOCAL_BASE = r"\\adair-file2\RnD\RDrive\R&D\STAFF FOLDERS\PariC\Sensor_logs\all"
OUTPUT_BASE = r"\\adair-file2\RnD\RDrive\R&D\STAFF FOLDERS\PariC\Sensor_logs"


# === STEP 1: Map date -> folder number (yesterday) ===
def get_folder_number_for_today():
    base_folder = 20402
    base_date = datetime.date(2025, 11, 10)

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    day_offset = (yesterday - base_date).days
    folder_number = base_folder + day_offset

    # e.g., "10Nov"
    day_label = yesterday.strftime("%d%b").capitalize()
    return str(folder_number), day_label


# === STEP 2: High-speed download using gsutil ===
def download_gcs_folder(bucket_name, prefix, local_path):
    """Download from GCS using gsutil -m cp for parallel speed."""
    os.makedirs(local_path, exist_ok=True)

    # Convert Windows backslashes to forward slashes for gsutil
    local_path_fixed = local_path.replace("\\", "/")

    src = f"gs://{bucket_name}/{prefix}"
    print(f"Running: gsutil -m cp -r {src} \"{local_path_fixed}\"")

    try:
        # Explicit path to gsutil for reliability (bypasses PATH issues)
        GSUTIL_PATH = r"C:\Users\PariC\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gsutil.cmd"

        # Ensure destination folder exists (gsutil won't auto-create)
        os.makedirs(local_path, exist_ok=True)

        # Run gsutil
        subprocess.run(
            [GSUTIL_PATH, "-m", "cp", "-r", src, local_path],
            check=True,
            capture_output=True,
            text=True
        )

        return True
    except subprocess.CalledProcessError as e:
        print(f"gsutil failed for {prefix}: {e.stderr or str(e)}")
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
        combine_files(local_path, output_file)
        #shutil.rmtree(local_path)
        #print(f"Cleaned up temporary folder: {local_path}")
    else:
        print(f"Skipping {name} — no files found or gsutil failed.")


# === MAIN ===
def main():
    folder_num, day_label = get_folder_number_for_today()
    print(f"\n=== Starting log combine for {day_label} (folder {folder_num}) ===")

    for name in IDS:
        process_user(name, folder_num, day_label)

    print("\n All users processed successfully.")


if __name__ == "__main__":
    main()

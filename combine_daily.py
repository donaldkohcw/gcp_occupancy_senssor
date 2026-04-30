import argparse
import datetime
import os
from zoneinfo import ZoneInfo
from google.cloud import storage
from google.auth import default as auth_default
from google.auth.exceptions import DefaultCredentialsError

# === CONFIG ===
BUCKET = "aaai_bucket"
PROJECT = "aaaiai"
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


# === STEP 2: Download using google-cloud-storage Python library ===
def download_gcs_folder(bucket_name, prefix, local_path):
    """Download from GCS using the google-cloud-storage Python library."""
    os.makedirs(local_path, exist_ok=True)

    src = f"gs://{bucket_name}/{prefix}"
    print(f"Requested copy: {src} -> \"{local_path}\"")

    try:
        client = storage.Client(project=PROJECT)
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        if not blobs:
            print(f"No files found in {src}")
            return False
        
        for blob in blobs:
            # Skip empty "folder" blobs
            if blob.name.endswith('/'):
                continue
            
            # Extract file name and create local directory structure
            relative_path = blob.name[len(prefix):]
            local_file = os.path.join(local_path, relative_path)
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            # Download the blob
            blob.download_to_filename(local_file)
            print(f"Downloaded: {blob.name}")
        
        return True
    except DefaultCredentialsError as e:
        print(f"\n[ERROR] Authentication failed: {str(e)}")
        print("\nPlease authenticate with Google Cloud:")
        print("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable to a service account key JSON file")
        print("   Example: $env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\\path\\to\\key.json'")
        print("\nOR")
        print("2. Run: python authenticate_gcp.py (and follow the browser login)")
        return False
    except Exception as e:
        print(f"Failed to download from {src}: {str(e)}")
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
    # Check if credentials are available
    try:
        auth_default()
    except DefaultCredentialsError:
        print("[ERROR] Google Cloud credentials not found!")
        print("\nTo set up authentication:")
        print("\n1. If you have a service account key JSON file:")
        print("   Set the environment variable:")
        print("   $env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\\path\\to\\service-account-key.json'")
        print("   Then run this script again.")
        print("\n2. If you don't have a key file:")
        print("   a) Go to: https://console.cloud.google.com/")
        print("   b) Create a service account and download the JSON key")
        print("   c) Set the environment variable as shown above")
        return
    
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

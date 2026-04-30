#!/usr/bin/env python3
"""
One-time setup script to configure GCP credentials for automatic use.
Just put your service account JSON key in the same folder as this script.
"""

import os
import json
import sys
from pathlib import Path

def setup_credentials():
    """Find and configure the GCP credentials automatically."""
    script_dir = Path(__file__).parent
    
    # Look for any .json file that looks like a service account key
    json_files = list(script_dir.glob("*.json"))
    
    if not json_files:
        print("\n[ERROR] No JSON credentials file found!")
        print("\nSteps to get your credentials:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Select your project")
        print("3. Go to 'Service Accounts' (search in top bar)")
        print("4. Click on a service account (create one if needed)")
        print("5. Go to 'Keys' tab")
        print("6. Click 'Add Key' → 'Create new key' → 'JSON'")
        print("7. Save the downloaded .json file in this folder:")
        print(f"   {script_dir}")
        print("\nThen run this setup script again.")
        return False
    
    creds_file = json_files[0]
    
    # Verify it's a valid service account key
    try:
        with open(creds_file, 'r') as f:
            data = json.load(f)
        if 'type' not in data or data['type'] != 'service_account':
            print(f"[WARNING] {creds_file.name} doesn't look like a service account key")
            return False
    except json.JSONDecodeError:
        print(f"[ERROR] {creds_file.name} is not valid JSON")
        return False
    
    # Set environment variable for this session
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_file.absolute())
    
    print(f"✓ Found credentials: {creds_file.name}")
    print(f"✓ Set GOOGLE_APPLICATION_CREDENTIALS to: {creds_file.absolute()}")
    
    # Create a batch file to persist the environment variable
    batch_file = script_dir / "set_credentials.bat"
    with open(batch_file, 'w') as f:
        f.write(f'@echo off\n')
        f.write(f'set "GOOGLE_APPLICATION_CREDENTIALS={creds_file.absolute()}"\n')
        f.write(f'echo GCP credentials configured\n')
    
    print(f"✓ Created {batch_file.name} to persist credentials")
    print("\nTo use this automatically in PowerShell, run:")
    print(f"  .\\set_credentials.bat")
    print("  python .\\combine_daily.py --folder 20573")
    
    return True

if __name__ == '__main__':
    if setup_credentials():
        print("\n✓ Setup complete! You can now run the scripts.")
        sys.exit(0)
    else:
        print("\n✗ Setup failed.")
        sys.exit(1)

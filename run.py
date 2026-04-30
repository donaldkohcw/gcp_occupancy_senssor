#!/usr/bin/env python3
"""
Wrapper script that handles setup and runs combine_daily.py automatically.
Just run this and everything else is automatic.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def setup_credentials_if_needed():
    """Setup credentials if not already configured."""
    # Check if credentials are already set
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print(f"✓ Credentials already configured")
        return True
    
    script_dir = Path(__file__).parent
    json_files = list(script_dir.glob("*.json"))
    
    if json_files:
        creds_file = json_files[0]
        try:
            with open(creds_file, 'r') as f:
                data = json.load(f)
            if data.get('type') == 'service_account':
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_file.absolute())
                print(f"✓ Credentials configured: {creds_file.name}")
                return True
        except:
            pass
    
    # No credentials found - show error
    print("\n[ERROR] GCP credentials not found!")
    print("\nTo set up automatically:")
    print("1. Download your service account JSON key from Google Cloud Console")
    print("2. Save it in this folder")
    print("3. Run this script again")
    print("\nLearn how: https://cloud.google.com/docs/authentication/application-default-credentials")
    return False

def run_combine_daily(args):
    """Run combine_daily.py with the given arguments."""
    script_dir = Path(__file__).parent
    combine_script = script_dir / "combine_daily.py"
    
    if not combine_script.exists():
        print(f"[ERROR] combine_daily.py not found at {combine_script}")
        return False
    
    cmd = [sys.executable, str(combine_script)] + args
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    return result.returncode == 0

if __name__ == '__main__':
    # Setup credentials if needed
    if not setup_credentials_if_needed():
        sys.exit(1)
    
    # Run combine_daily.py with any command line arguments
    success = run_combine_daily(sys.argv[1:])
    sys.exit(0 if success else 1)

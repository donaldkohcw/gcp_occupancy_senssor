#!/usr/bin/env python3
"""
Helper script to authenticate with Google Cloud without needing gcloud CLI.
Uses the google-auth-oauthlib library for browser-based authentication.
"""

import os
import json
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for Cloud Storage access
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

def authenticate():
    """Authenticate and save credentials for use by the script."""
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
            print(f"Loaded existing credentials from {TOKEN_FILE}")
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"\nERROR: {CREDENTIALS_FILE} not found!")
                print("\nTo authenticate, you need to:")
                print("1. Go to: https://console.cloud.google.com/")
                print("2. Create a service account key (JSON format)")
                print("3. Download it and save as 'credentials.json' in this directory")
                print("\nAlternatively, you can create an OAuth 2.0 Desktop Application:")
                print("1. Go to: https://console.cloud.google.com/apis/credentials")
                print("2. Click 'Create Credentials' > 'OAuth 2.0 Client ID'")
                print("3. Choose 'Desktop application'")
                print("4. Download and save as 'credentials.json'")
                return False
            
            print(f"Loading credentials from {CREDENTIALS_FILE}...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("Authentication successful!")
        
        # Save credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f"Credentials saved to {TOKEN_FILE}")
    
    # Set Application Default Credentials environment variable
    # (This makes the Google Cloud libraries use these credentials automatically)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(TOKEN_FILE)
    print(f"Set GOOGLE_APPLICATION_CREDENTIALS to {TOKEN_FILE}")
    
    return True

if __name__ == '__main__':
    if authenticate():
        print("\n✓ Authentication complete! You can now run combine_daily.py")
    else:
        print("\n✗ Authentication failed. Please set up credentials first.")

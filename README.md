📥 GCP Daily Log Downloader & Combiner

This repository contains a small utility that automatically downloads daily log folders from a Google Cloud Storage bucket and combines all files into a single log file per user.
It is designed to run on a Windows machine via a scheduled PowerShell task.

📌 Files
1. combine_daily.py

      Python script that:
   
      1)Computes yesterday’s folder index
   
      2)Downloads each user’s logs from GCS using gsutil
   
      3)Stores them in a local UNC path
   
      4)Concatenates all log files into a single .txt output
   
      5)Runs once per day
   
      6)Users + folder mapping + bucket are hard-coded in the script.
   
      7)Source: combine_daily.py 

3. run_combine.ps1 : PowerShell wrapper used for scheduling.

      It typically:
   
         -Activates your Python environment (if needed)
   
         -Runs python combine_daily.py
   
         -Logs output for debugging
   
         -Is triggered via Windows Task Scheduler (cron equivalent)
   
         -This is what your scheduled daily job runs.
   

6. requirements.txt

   Minimal dependencies required by the script:
   
   Install them with:
  
  pip install -r requirements.txt

************ Running Manually ****************

python combine_daily.py

This will:

  Determine yesterday’s GCS folder number
  
  Download logs for all configured users
  
  Combine logs into output files in the defined UNC folder
  

⚙️ Scheduling (Windows Task Scheduler)

  Open Task Scheduler
  
  Create a new task
  
  Trigger: Daily (e.g., 2:00 AM)
  
  Action: Start a program
  
  Program/script: powershell.exe
  
  Add arguments:
  
  -ExecutionPolicy Bypass -File "path\to\run_combine.ps1"


Ensure the task runs with proper permissions for ( give full access to your user in permisson settings):

  UNC file paths
  
  gsutil access
  
  Python environment
  
  📂 Output Structure :For each user, logs are saved to:
  
  <OUTPUT_BASE>/<UserName>/<DateLabel>_<UserName>.txt      
  
  Example log : Sensor_logs/Marg/10Nov_Marg.txt

🛠 Requirements

  Python 3.8+
  
  gsutil installed with Google Cloud SDK
  
  Access to GCS bucket
  
  Windows environment (PowerShell + Task Scheduler)

🧩 Notes : Temporary download folders are kept unless you uncomment the cleanup lines

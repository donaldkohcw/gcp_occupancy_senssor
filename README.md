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

📅 Daily Automation (run_daily_auto.ps1 + run_process_all_users.py)

  run_daily_auto.ps1 is the scheduled entry point (Windows Task Scheduler task "GCP_Occupancy_Daily", daily at 08:30, logon type Interactive so the mapped V: drive is available). It runs, in order:

  1) python combine_daily.py (no args) — downloads/combines yesterday's and today's folders.

  2) python run_process_all_users.py --<folder> — once for yesterday's folder number and once for today's, each derived from the date using the same BASE_FOLDER_NUM (20402) / BASE_DATE (2025-11-10) mapping combine_daily.py uses internally, so no folder number ever needs manual updating.

  Output/errors are appended to run_daily_auto.log next to the script.

  To inspect or change the schedule: Task Scheduler > Task Scheduler Library > GCP_Occupancy_Daily.

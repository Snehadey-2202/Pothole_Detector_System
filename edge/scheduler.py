import schedule
import time
import os
import sys

from detector import run_detection_cycle

def job():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled detection cycle...")
    run_detection_cycle()

if __name__ == "__main__":
    print("Starting cron job simulator...")
    # Run once immediately
    job()
    
    # Schedule every 10 seconds for demo purposes
    # In reality, this might be every few minutes on a Raspberry Pi
    schedule.every(10).seconds.do(job)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Scheduler stopped.")

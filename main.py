import subprocess
import webbrowser
import time

# Start motion detector in a new process
subprocess.Popen(["python", "motion_detector.py"])

# Start Flask admin panel in a new process
subprocess.Popen(["python", "app.py"])

# Wait a bit so Flask can start
time.sleep(2)

# Open dashboard automatically in browser
webbrowser.open("http://localhost:5000")

print("AutoGuard started successfully.")
print("Motion detector is running.")
print("Admin panel is opening in your browser.")
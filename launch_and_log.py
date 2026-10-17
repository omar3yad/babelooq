import subprocess
import sys

with open("uvicorn_boot.log", "w", encoding="utf-8") as f:
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"], stdout=f, stderr=f, cwd="D:\\Project\\Garage_Bundle\\garage4u")
    import time
    time.sleep(3)
    print("PID:", p.pid, "poll:", p.poll())

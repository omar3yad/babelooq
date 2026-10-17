import os
import sys
import traceback

with open("server_debug.log", "w", encoding="utf-8") as f:
    try:
        f.write(f"Starting server with {sys.executable}\n")
        f.flush()
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="debug")
    except Exception as e:
        f.write(f"Error: {traceback.format_exc()}\n")
        f.flush()

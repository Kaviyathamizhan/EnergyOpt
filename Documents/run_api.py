r"""
run_api.py -- Launch script for the FastAPI inference engine.
Run from the project root:
    venv\Scripts\python.exe run_api.py
"""
import sys
import os

# Ensure the project root is on the Python path BEFORE uvicorn loads the app
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)

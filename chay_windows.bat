@echo off
pip install -r requirements.txt
start http://localhost:8000
uvicorn api.main:app --port 8000
pause

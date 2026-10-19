#!/bin/sh
pip install -r requirements.txt
uvicorn api.main:app --port 8000

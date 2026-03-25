#!/bin/bash
cd "$(dirname "$0")"

# Optional: set up virtual env if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo "FastAPI backend started in the background on port 8000"

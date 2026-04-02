#!/bin/bash
set -e

cd /home/ubuntu/legal

# Activate venv
source venv/bin/activate

# Build frontend if needed
if [ ! -d "frontend/build" ] || [ "frontend/src" -nt "frontend/build" ]; then
    echo "=== 프론트엔드 빌드 ==="
    cd frontend && npm run build && cd ..
fi

echo "=== 서버 시작 (http://localhost:8000) ==="
uvicorn backend.main:app --host 0.0.0.0 --port 8000

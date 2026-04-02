#!/usr/bin/env python3
"""법률 데이터 인덱싱 실행 스크립트."""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Clone laws
print("=== 법률 데이터 클론 ===")
subprocess.run(
    ["bash", os.path.join(ROOT, "scripts", "clone_laws.sh")], check=True
)

# 2. Index
print("\n=== 인덱싱 ===")
os.chdir(ROOT)
subprocess.run([sys.executable, "-m", "backend.rag.indexer"], check=True)

print("\n=== 완료 ===")

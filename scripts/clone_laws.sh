#!/bin/bash
set -e

DATA_DIR="/home/ubuntu/legal/backend/data/laws"
REPO_URL="https://github.com/legalize-kr/legalize-kr.git"

if [ -d "$DATA_DIR/repo" ]; then
    echo "Laws directory already exists, skipping clone"
    exit 0
fi

mkdir -p "$DATA_DIR"

# Sparse checkout: only election-related laws
git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$DATA_DIR/repo"
cd "$DATA_DIR/repo"
git sparse-checkout set \
    "kr/공직선거법" \
    "kr/정치자금법" \
    "kr/정당법" \
    "kr/공직선거관리규칙"

echo "Done. Laws cloned to $DATA_DIR/repo/kr/"
ls -la kr/

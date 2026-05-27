#!/bin/bash
set -e

echo "=== Building frontend ==="
cd frontend
npm install
npm run build

echo "=== Copying to backend/static ==="
rm -rf ../backend/static
cp -r dist ../backend/static

echo "=== Done! Run with: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 ==="

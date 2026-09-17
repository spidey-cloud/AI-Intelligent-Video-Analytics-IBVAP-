#!/usr/bin/env bash
# Fetch demo assets for the IBVAP reference build (no GPU, CPU-only).
set -e
cd "$(dirname "$0")/.."
mkdir -p models data/videos

echo "[1/2] YOLOv8n weights (6 MB)..."
curl -fL --retry 2 -o models/yolov8n.pt \
  "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"

echo "[2/2] Demo footage (short crosswalk clip, public archive)..."
curl -fL --retry 2 -o data/videos/crosswalk.mp4 \
  "https://archive.org/download/codtx-Walk_Sign_Is_On_Denton_crosswalk/Walk_Sign_Is_On_Denton_crosswalk.mp4" \
  || echo "   (skipped — recorded-footage camera disabled, synthetic cameras unaffected)"

echo "Done."

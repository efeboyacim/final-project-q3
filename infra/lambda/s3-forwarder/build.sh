#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf build; mkdir -p build
pip install -r requirements.txt -t build/
cp handler.py build/
cd build && zip -r ../s3-forwarder.zip .
echo "Created infra/lambda/s3-forwarder/s3-forwarder.zip"

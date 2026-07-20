#!/bin/bash
# Run backend unit tests.
# Usage: ./scripts/run_tests.sh [pytest-args...]
set -e
cd "$(dirname "$0")/.."
echo "=== Blog Feed Backend Tests ==="
conda run -n blog python3 -m pytest tests/ -v "$@"


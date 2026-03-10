#!/bin/bash
# fix_and_scan.sh

set -e

if [ -z "$1" ]; then
    echo "Error: Please provide a SonarQube token."
    echo "Usage: ./fix_and_scan.sh <token>"
    exit 1
fi

TOKEN="$1"

echo "STEP 1: Checking for docker and running pytest..."
# if coverage.xml already exists purely for our test, we'll speed it up by skipping if requested, 
# but as per instructions we run pytest in Docker:
if ! docker exec uber_backend pytest tests/ \
    --create-db \
    --cov=apps \
    --cov=consumers \
    --cov-report=xml:/app/coverage.xml \
    --cov-branch \
    -p no:warnings -q; then
    echo "⚠️ Warning: Pytest had failing tests or exited with non-zero. Continuing."
fi

echo "STEP 2: Copying coverage.xml out of Docker..."
if ! docker cp uber_backend:/app/coverage.xml backend/coverage.xml; then
    echo "❌ Error: Failed to copy coverage.xml from container."
    exit 1
fi

echo "STEP 3: Fixing ALL path mismatches via Python constraint..."
python3 python_fix_coverage.py

echo "STEP 4: Validating fix..."
python3 debug_sonar_paths.py | grep -i "MISSING" && exit 1 || echo "✅ Validation Passed!"

echo "STEP 5: Running SonarQube scanner..."
if ! ./run-sonar.sh "$TOKEN"; then
    echo "❌ Error: SonarQube scan failed."
    exit 1
fi

echo "STEP 6: Showing Result..."
echo "✅ Scan completed successfully. All paths are resolved!"
echo "Dashboard URL: http://localhost:9000/dashboard?id=uber_backend-clone"

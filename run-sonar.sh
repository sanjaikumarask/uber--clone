#!/bin/bash
# run-sonar.sh
# Expected to be executed by fix_and_scan.sh or directly if paths are already fixed.

SONAR_TOKEN="$1"
SONAR_HOST_URL=${SONAR_HOST_URL:-"http://localhost:9000"}

if [ -z "$SONAR_TOKEN" ]; then
    echo "Error: Running without SONAR_TOKEN."
    echo "Usage: ./run-sonar.sh <your_generated_token>"
    exit 1
fi

echo "Clearing old scanner cache (to ensure fresh resolution)..."
rm -rf .scannerwork/

echo "Running Sonar Scanner with Token authentication..."
docker run \
    --rm \
    --network host \
    -v "$(pwd):/usr/src" \
    sonarsource/sonar-scanner-cli \
    -Dsonar.host.url="$SONAR_HOST_URL" \
    -Dsonar.token="$SONAR_TOKEN"

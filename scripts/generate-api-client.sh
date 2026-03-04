#!/usr/bin/env bash
# Generate TypeScript API client from OpenAPI schema
#
# Prerequisites:
#   npm install -g @openapitools/openapi-generator-cli
#   OR use Docker: docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli
#
# Usage:
#   ./scripts/generate-api-client.sh [api_url]

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
OUTPUT_DIR="plexaddons-web/src/generated"
SPEC_FILE="/tmp/plexaddons-openapi.json"

echo "Fetching OpenAPI schema from ${API_URL}..."
curl -sf "${API_URL}/openapi.json" -o "$SPEC_FILE"

echo "Generating TypeScript client..."
if command -v openapi-generator-cli &> /dev/null; then
    openapi-generator-cli generate \
        -i "$SPEC_FILE" \
        -g typescript-fetch \
        -o "$OUTPUT_DIR" \
        --additional-properties=supportsES6=true,typescriptThreePlus=true,npmName=plexaddons-client \
        --skip-validate-spec
elif command -v docker &> /dev/null; then
    docker run --rm \
        -v "${PWD}:/local" \
        -v "${SPEC_FILE}:/spec/openapi.json" \
        openapitools/openapi-generator-cli generate \
        -i /spec/openapi.json \
        -g typescript-fetch \
        -o "/local/${OUTPUT_DIR}" \
        --additional-properties=supportsES6=true,typescriptThreePlus=true,npmName=plexaddons-client \
        --skip-validate-spec
else
    echo "ERROR: openapi-generator-cli or Docker is required"
    echo "Install: npm install -g @openapitools/openapi-generator-cli"
    exit 1
fi

echo "Generated client at ${OUTPUT_DIR}/"
echo "Files:"
find "$OUTPUT_DIR" -name "*.ts" | head -20

rm -f "$SPEC_FILE"
echo "Done."

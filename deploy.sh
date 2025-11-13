#!/bin/bash
# Deploy Databricks App with the correct config
# Usage: ./deploy.sh <target> [profile]
#   Example: ./deploy.sh dev-lakebridge adb1
#   Target format: <environment>-<project> (e.g., dev-myproject, prod-ucx)

set -e

[ $# -eq 0 ] && echo "Usage: $0 <target> [profile]" && exit 1

TARGET=$1
PROFILE=${2:-""}

# Extract project name from target (everything after the first dash)
if [[ $TARGET == *"-"* ]]; then
    PROJECT="${TARGET#*-}"
else
    echo "Error: Target must be in format <environment>-<project>"
    exit 1
fi

# Copy app config
SOURCE="webapp/app_configs/app.${PROJECT}.yaml"
[ ! -f "$SOURCE" ] && echo "Error: $SOURCE not found" && exit 1

echo "Deploying $PROJECT → $TARGET"
cp "$SOURCE" "webapp/app.yaml"

# Deploy bundle
CMD="databricks bundle deploy --target $TARGET"
[ -n "$PROFILE" ] && CMD="$CMD --profile $PROFILE"
$CMD

echo "✓ Deployment complete"

# Grant permissions to serving endpoint
APP_NAME="${TARGET}-ucx-assistant"
ENDPOINT_NAME=$(grep -A1 "SERVING_ENDPOINT" "$SOURCE" | grep "value:" | awk '{print $2}' | tr -d '"')
SP_ID=$(databricks apps get "$APP_NAME" ${PROFILE:+--profile $PROFILE} -o json | grep -o '"service_principal_client_id":"[^"]*"' | cut -d'"' -f4)

# Get the actual endpoint ID
ENDPOINT_ID=$(databricks serving-endpoints get "$ENDPOINT_NAME" ${PROFILE:+--profile $PROFILE} -o json | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

[ -n "$SP_ID" ] && [ -n "$ENDPOINT_ID" ] && databricks permissions update serving-endpoints "$ENDPOINT_ID" --json "{\"access_control_list\":[{\"service_principal_name\":\"$SP_ID\",\"permission_level\":\"CAN_QUERY\"}]}" ${PROFILE:+--profile $PROFILE} && echo "✓ Permissions granted"

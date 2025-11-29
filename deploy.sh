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

# Try to get AUDIT_TABLE from app.yaml, fall back to config file
AUDIT_TABLE=$(grep -A1 "name: AUDIT_TABLE" "$SOURCE" | grep "value:" | awk '{print $2}' | tr -d '"')

if [ -z "$AUDIT_TABLE" ]; then
    # Fall back to config file
    CONFIG_FILE=$(grep -A1 "name: CONFIG_FILE" "$SOURCE" | grep "value:" | awk '{print $2}' | tr -d '"')
    if [ -n "$CONFIG_FILE" ]; then
        AUDIT_TABLE=$(grep "^  audit_table:" "webapp/$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
        echo "ℹ️  Using audit table from config file: $AUDIT_TABLE"
    fi
fi

# Add AUDIT_TABLE to app.yaml if found
if [ -n "$AUDIT_TABLE" ]; then
    cat >> "webapp/app.yaml" << EOF
  - name: AUDIT_TABLE
    value: "$AUDIT_TABLE"
EOF
fi

# Deploy bundle
CMD="databricks bundle deploy --target $TARGET"
[ -n "$PROFILE" ] && CMD="$CMD --profile $PROFILE"
$CMD

echo "✓ Deployment complete"

# Grant permissions to serving endpoint
APP_NAME="${TARGET}-repo-assistant"

# Try to get SERVING_ENDPOINT from app.yaml, fall back to config file
ENDPOINT_NAME=$(grep -A1 "name: SERVING_ENDPOINT" "$SOURCE" | grep "value:" | awk '{print $2}' | tr -d '"')

if [ -z "$ENDPOINT_NAME" ]; then
    # Fall back to config file
    CONFIG_FILE=$(grep -A1 "name: CONFIG_FILE" "$SOURCE" | grep "value:" | awk '{print $2}' | tr -d '"')
    if [ -n "$CONFIG_FILE" ]; then
        ENDPOINT_NAME=$(grep "^  serving_endpoint:" "webapp/$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
        echo "ℹ️  Using serving endpoint from config file: $ENDPOINT_NAME"
    fi
fi

SP_ID=$(databricks apps get "$APP_NAME" ${PROFILE:+--profile $PROFILE} -o json | grep -o '"service_principal_client_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$SP_ID" ]; then
    # Extract catalog and schema from audit_table in config file
    CONFIG_FILE=$(grep -A1 "name: CONFIG_FILE" "$SOURCE" | grep "value:" | awk '{print $2}' | tr -d '"')
    if [ -n "$CONFIG_FILE" ]; then
        AUDIT_TABLE=$(grep "^  audit_table:" "webapp/$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
        if [ -n "$AUDIT_TABLE" ]; then
            CATALOG=$(echo "$AUDIT_TABLE" | cut -d'.' -f1)
            SCHEMA=$(echo "$AUDIT_TABLE" | cut -d'.' -f2)
            
            # Grant USE CATALOG permission
            echo "Granting USE CATALOG on $CATALOG to service principal..."
            databricks grants update catalog "$CATALOG" --json "{\"changes\":[{\"principal\":\"$SP_ID\",\"add\":[\"USE_CATALOG\"]}]}" ${PROFILE:+--profile $PROFILE} && echo "✓ USE CATALOG granted on $CATALOG"
            
            # Grant READ and WRITE permissions on schema
            echo "Granting READ and WRITE on schema $CATALOG.$SCHEMA to service principal..."
            databricks grants update schema "$CATALOG.$SCHEMA" --json "{\"changes\":[{\"principal\":\"$SP_ID\",\"add\":[\"USE_SCHEMA\",\"SELECT\",\"MODIFY\", \"CREATE TABLE\"]}]}" ${PROFILE:+--profile $PROFILE} && echo "✓ Schema permissions granted on $CATALOG.$SCHEMA"
        fi
    fi
fi

# Get the actual endpoint ID (suppress error if endpoint doesn't exist yet)
ENDPOINT_ID=$(databricks serving-endpoints get "$ENDPOINT_NAME" ${PROFILE:+--profile $PROFILE} -o json 2>/dev/null | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$SP_ID" ] && [ -n "$ENDPOINT_ID" ]; then
    databricks permissions update serving-endpoints "$ENDPOINT_ID" --json "{\"access_control_list\":[{\"service_principal_name\":\"$SP_ID\",\"permission_level\":\"CAN_QUERY\"}]}" ${PROFILE:+--profile $PROFILE} && echo "✓ Endpoint permissions granted"
elif [ -z "$ENDPOINT_ID" ]; then
    echo "⚠ Warning: Endpoint '$ENDPOINT_NAME' does not exist yet. Skipping endpoint permissions setup."
    echo "  Endpoint permissions will be configured after the agent endpoint is created."
fi

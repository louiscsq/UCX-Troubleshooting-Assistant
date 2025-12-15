# Lakebridge Assistant - Quick Deployment Guide

Simple deployment instructions for the Lakebridge Troubleshooting Assistant.

## Prerequisites

- Databricks workspace with Unity Catalog
- Databricks CLI v0.218+ installed and configured
- Admin privileges
- Access to Claude Sonnet 4.5 foundation model
- Vector Search endpoint (create one if needed)
- Unity Catalog catalog and schema

## Deployment Steps

### 1. Configure Target

Edit `targets/lakebridge.yml` and set your workspace URL:

```yaml
workspace:
  host: https://your-workspace.databricks.com/
```

### 2. Configure Variables

Edit `databricks.yml` and set:

```yaml
variables:
  vector_search_endpoint: "your_vector_search_endpoint"
  catalog_name: "your_catalog"
  schema_name: "your_schema"
```

### 3. Deploy Resources

```bash
./deploy.sh dev-lakebridge

# Or with a specific Databricks profile
./deploy.sh dev-lakebridge myprofile
```

This deploys:
- Data ingestion workflow (`w01_data_ingestion_and_setup`)
- Agent deployment workflow (`w02_build_agent_and_deploy`)
- Streamlit web app

### 4. (Optional) Upload Internal Documents

Upload PDFs, DOCX, PPTX, or images to `/Workspace/Shared/lakebridge` for indexing.

### 5. Run Data Ingestion

```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-lakebridge --param github_token="your_github_token"
```

Takes ~30 minutes. Indexes Lakebridge codebase and documentation.

### 6. Deploy Agent

```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-lakebridge
```

Takes ~5-10 minutes. Creates and deploys the MLflow agent.

### 7. Grant Permissions

```bash
./deploy.sh dev-lakebridge

# Or with a specific Databricks profile
./deploy.sh dev-lakebridge myprofile
```

Grants app permissions to query the serving endpoint and write audit logs.

### 8. Start the App

```bash
databricks bundle run app_assistant -t dev-lakebridge

# Or with a specific Databricks profile
databricks bundle run app_assistant -t dev-lakebridge --profile myprofile
```

This command starts the Streamlit application. Now that the agent endpoint is deployed and permissions are granted, the app will be fully functional.

### 9. Access App

```bash
databricks apps get dev-lakebridge-repo-assistant
```

Use the URL from the output to access your assistant.

## Configuration

Customize UI, prompts, and behavior by editing `webapp/configs/lakebridge.config.yaml`.

After changes, redeploy and restart:

```bash
./deploy.sh dev-lakebridge
databricks bundle run app_assistant -t dev-lakebridge

# Or with a specific Databricks profile
./deploy.sh dev-lakebridge myprofile
databricks bundle run app_assistant -t dev-lakebridge --profile myprofile
```

## Admin Dashboard

Access usage analytics:

```
https://your-app-url.databricksapps.com?admin=dashboard
```

## Troubleshooting

**No vector search endpoint:** Create one at Compute → Vector Search → Create Endpoint

**Schema doesn't exist:** Create catalog and schema first, then update `databricks.yml`

**GitHub rate limits:** Use `--param github_token="your_token"` in Step 5

**Permission errors:** Ensure you ran `./deploy.sh dev-lakebridge` after Step 6

## Refresh Knowledge Base

To update with latest Lakebridge code/documentation:

```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-lakebridge --param github_token="your_github_token"
```

Agent automatically uses updated indexes.


# UCX Assistant - Quick Deployment Guide

Simple deployment instructions for the UCX Troubleshooting Assistant.

## Prerequisites

- Databricks workspace with Unity Catalog
- Databricks CLI v0.218+ installed and configured
- Admin privileges
- Access to Claude Sonnet 4.5 foundation model
- Vector Search endpoint (create one if needed)
- Unity Catalog catalog and schema

## Deployment Steps

### 1. Configure Target

Edit `targets/ucx.yml` and set your workspace URL:

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
./deploy.sh dev-ucx
```

This deploys:
- Data ingestion workflow (`w01_data_ingestion_and_setup`)
- Agent deployment workflow (`w02_build_agent_and_deploy`)
- Streamlit web app

### 4. (Optional) Upload Internal Documents

Upload PDFs, DOCX, PPTX, or images to `/Workspace/Shared/ucx` for indexing.

### 5. Run Data Ingestion

```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-ucx --param github_token="your_github_token"
```

Takes ~30 minutes. Indexes UCX codebase and documentation.

### 6. Deploy Agent

```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-ucx
```

Takes ~5-10 minutes. Creates and deploys the MLflow agent.

### 7. Grant Permissions

```bash
./deploy.sh dev-ucx
```

Grants app permissions to query the serving endpoint and write audit logs.

### 8. Access App

```bash
databricks apps get dev-ucx-repo-assistant
```

Use the URL from the output to access your assistant.

## Configuration

Customize UI, prompts, and behavior by editing `webapp/configs/ucx.config.yaml`.

After changes, redeploy:

```bash
./deploy.sh dev-ucx
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

**Permission errors:** Ensure you ran `./deploy.sh dev-ucx` after Step 6

## Refresh Knowledge Base

To update with latest UCX code/documentation:

```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-ucx --param github_token="your_github_token"
```

Agent automatically uses updated indexes.


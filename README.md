# UCX Troubleshooting Assistant

AI-powered assistant for Unity Catalog Migration (UCX) troubleshooting. Uses Claude Sonnet 4 with vector search over UCX codebase and documentation.

![UCX Logo](https://github.com/databrickslabs/ucx/raw/main/docs/ucx/static/img/ucx.png)

## Features

- Dual vector search indexes (codebase + documentation)
- AI agent with tool calling and reasoning
- Delta Lake audit logging with dashboard
- Source attribution for all answers

## Architecture

- **Data Ingestion**: Downloads UCX code/docs, generates AI summaries, creates vector indexes
- **Agent Deployment**: MLflow agent with vector search tools, deployed to model serving
- **Web App**: Streamlit UI with chat interface and audit dashboard
- **Configuration**: `webapp/config.yaml` for all settings

## Installation & Deployment

### Prerequisites
- Databricks workspace with Unity Catalog
- Databricks CLI v0.218+
- Workspace admin privileges
- Access to Claude Sonnet 4.5 and Claude Sonnet 4
- Unity Catalog schema with write permissions
- (Optional) GitHub token for API rate limits

### Quick Deploy

#### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd UCX-Troubleshooting-Assistant
```

#### Step 2: Configure databricks.yml
Edit required variables:
```yaml
variables:
  vector_search_endpoint: "your_vector_search_endpoint"
  schema: "catalog_name.schema_name"
targets:
  dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com/
```

#### Step 3: Deploy Resources
```bash
databricks bundle deploy
```

#### Step 4: Run Data Ingestion (~20 minutes)
```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_github_token"  # Optional but recommended
```

#### Step 5: Deploy Agent (~5-10 minutes)
```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
```

Wait for endpoint to be ready:
```bash
databricks serving-endpoints get --name "agents_{schema}-ucx_agent"
```

#### Step 6: Configure webapp/config.yaml
```yaml
deployment:
  serving_endpoint: "agents_main-default-ucx_agent"
  audit_table: "catalog.schema.ucx_chat_interactions"
```

#### Step 7: Grant Permissions
Via Databricks UI:
- Model endpoint: Grant "CAN QUERY" to App Service Principal (`{target}-{bundle_name}`)
- Catalog/Schema: Grant "Data Editor" to App Service Principal

#### Step 8: Deploy and Start App
```bash
databricks bundle deploy
databricks bundle run dev-ucx-assistant
```

Access URL:
```bash
databricks apps get dev-ucx-assistant
```

## Project Structure

```
UCX-Troubleshooting-Assistant/
├── 01_data_ingestion_and_setup/    # Ingest code/docs, create vector indexes
├── 02_build_agent_and_deploy/      # Build and deploy MLflow agent
├── webapp/
│   ├── config.yaml                  # Application configuration
│   ├── app.py                       # Streamlit chat interface
│   └── audit_*.py                   # Audit system
├── resources/                       # Workflow definitions
└── databricks.yml                   # Bundle configuration
```

## Audit & Compliance

### Configuration
```yaml
# webapp/config.yaml
deployment:
  audit_table: "catalog.schema.ucx_chat_interactions"
  audit_debug: false
```

### Audit Dashboard
Access: `https://your-app-url.databricksapps.com?admin=dashboard`

Features: Overview metrics, timeline analysis, user patterns, SQL analytics, CSV/JSON export

## Technical Details

### Models
- Claude Sonnet 4.5: Code summarization
- Claude Sonnet 4: Agent interactions
- databricks-gte-large-en: Embeddings

### Vector Indexes
- Codebase: Python/SQL with AI summaries
- Documentation: README files and guides

## Troubleshooting

### Common Issues
- **Vector endpoint fails**: Create manually via UI: Compute → Vector Search
- **Schema errors**: Ensure format is `catalog.schema`
- **API rate limits**: Use `--param github_token="token"` with ingestion job
- **Permission errors**: Grant CAN QUERY (endpoint) and Data Editor (catalog) to App Service Principal

### Refresh Knowledge Base
```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" --param github_token="token"
```

## Development

### Local Setup
```bash
python -m venv .venv
source .venv/bin/activate
cd webapp
pip install -r requirements.txt
```

Configure `webapp/config.yaml` and set Databricks credentials:
```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token"
streamlit run app.py
```

### Updating
- UI/deployment: Edit `webapp/config.yaml`, run `databricks bundle deploy`
- Agent behavior: Edit `webapp/config.yaml` agent section, run `databricks jobs run-now --job-name "w02_build_agent_and_deploy"`

## Links

- [UCX Repository](https://github.com/databrickslabs/ucx)
- [UCX Documentation](https://databrickslabs.github.io/ucx/)
- [Databricks Apps](https://docs.databricks.com/dev-tools/apps/)
- [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)

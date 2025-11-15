# Repository Troubleshooting Assistant

An AI assistant for troubleshooting repository-specific issues. Built with Streamlit, powered by Claude Sonnet 4.5, and enhanced with vector search over codebases and documentation. Configured by default for Unity Catalog Migration (UCX) but adaptable to any GitHub repository.

## Quick Start

1. Configure `databricks.yml` with workspace, vector search endpoint, and schema
2. Deploy resources: `databricks bundle deploy`
3. Run data ingestion: `databricks jobs run-now --job-name "w01_data_ingestion_and_setup"`
4. Deploy agent: `databricks jobs run-now --job-name "w02_build_agent_and_deploy"`
5. Customize config (optional): Edit `webapp/configs/ucx.config.yaml`
6. Deploy app: `./deploy.sh dev-ucx`

## Features

- Dual vector search over codebase and documentation
- Agent explains reasoning and strategy in real-time
- Provides source attribution with links to code and docs
- Multi-repository support with separate configs per project
- Delta Lake audit logging with admin dashboard
- Customizable UI text, prompts, and checklists per repository

## Architecture

```
Troubleshooting Assistant
├── Data Ingestion Workflow (w01_data_ingestion_and_setup)
│   ├── Ingest code from GitHub with AI summaries
│   ├── Ingest documentation
│   └── Create vector search indexes (codebase + docs)
│
├── Agent Build & Deploy Workflow (w02_build_agent_and_deploy)
│   ├── Create MLflow agent with vector search tools
│   └── Deploy to Databricks model serving
│
└── Streamlit Web Application (webapp/)
    ├── Chat interface (app.py)
    ├── Delta Lake audit system (audit_utils.py)
    └── Admin dashboard (audit_dashboard.py)
    └── Repository-specific configs (webapp/configs/)
```

### Key Components

**Data Ingestion:** Downloads code and docs from GitHub, generates AI summaries, creates vector search indexes

**Agent Deployment:** Builds MLflow agent with vector search tools, deploys to model serving

**Web Application:** Streamlit chat interface, Delta Lake audit logging, admin dashboard

## Installation & Deployment

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- Databricks CLI v0.218+
- Workspace administrator privileges
- Access to Claude Sonnet 4.5 foundation model
- Unity Catalog schema with write permissions
- GitHub personal access token (optional, avoids rate limits)

### Deployment Steps

#### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd UCX-Troubleshooting-Assistant
```

#### Step 2: Configure databricks.yml
Edit variables and add targets for each repository you want to support:
```yaml
variables:
  config_file:
    default: "configs/ucx.config.yaml"
  repo:
    default: "databrickslabs/ucx"
  project_prefix:
    default: "ucx"
  vector_search_endpoint:
    default: "your_vector_search_endpoint"  # ⚠️ REQUIRED
  schema:
    default: "catalog_name.schema_name"  # ⚠️ REQUIRED

targets:
  # UCX Assistant
  ucx-dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com/  # ⚠️ UPDATE
    variables:
      repo: "databrickslabs/ucx"
      config_file: "configs/ucx.config.yaml"
      project_prefix: "ucx"
    default: true
  
  # Add more repositories as needed
  # myrepo-dev:
  #   variables:
  #     repo: "myorg/myrepo"
  #     config_file: "configs/myrepo.config.yaml"
  #     project_prefix: "myrepo"
```

Key variables:
- `config_file`: Path to config within `webapp/configs/`
- `repo`: GitHub repository in `owner/repo` format
- `project_prefix`: Unique prefix for resources (tables, models, endpoints)
- `vector_search_endpoint`: Must exist (create via Databricks UI: Compute > Vector Search)
- `schema`: Format `catalog.schema`

#### Step 3: Deploy Resources

```bash
databricks bundle deploy
```

#### Step 4: Run Data Ingestion

```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_github_token"
```

Downloads code and docs from GitHub, generates AI summaries, creates vector indexes.

#### Step 5: Deploy Agent

```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
```

Builds and deploys MLflow agent to model serving endpoint.

#### Step 6: Customize Configuration (Optional)

Edit `webapp/configs/{project_prefix}.config.yaml` to customize UI text, prompts, and checklists.

#### Step 7: Deploy App

```bash
./deploy.sh <target> [profile]

# Examples:
./deploy.sh dev-ucx
./deploy.sh dev-lakebridge myprofile
```

The script automatically:
- Configures the app with correct settings
- Deploys the Databricks App
- Grants USE CATALOG permission to service principal
- Grants schema permissions (USE SCHEMA, SELECT, MODIFY)
- Grants CAN QUERY permission on serving endpoint

Get app URL:
```bash
databricks apps get <target>-ucx-assistant
```

Access admin dashboard: `https://your-app-url.databricksapps.com?admin=dashboard`

## Project Structure

```
UCX-Troubleshooting-Assistant/
├── 01_data_ingestion_and_setup/       # Ingest code/docs, create vector indexes
│   ├── ingest_codebase.py
│   ├── ingest_documentation.py
│   └── create_vector.py
│
├── 02_build_agent_and_deploy/         # Build and deploy MLflow agent
│   ├── agent.py
│   └── build_agent_and_deploy.py
│
├── resources/                         # Workflow and app definitions
│   ├── 01_data_ingestion_and_setup.job.yml
│   ├── 02_build_agent_and_deploy.job.yml
│   └── app_assistant.app.yml
│
├── webapp/                            # Streamlit application
│   ├── app.py                         # Main chat interface
│   ├── configs/                       # Repository-specific configurations
│   │   └── ucx.config.yaml           # UCX config (UI, prompts, etc.)
│   ├── audit_*.py                     # Audit system modules
│   ├── model_serving_utils.py         # Model serving interface
│   └── requirements.txt
│
└── databricks.yml                     # Bundle configuration
```

## Audit Logging

Tracks user interactions, questions, responses, and response times in Delta Lake.

Configure in `webapp/configs/{project_prefix}.config.yaml`:
```yaml
deployment:
  audit_table: "catalog.schema.table_name"
```

Access dashboard at: `https://your-app-url.databricksapps.com?admin=dashboard`

## Multi-Repository Support

Deploy separate assistants for different repositories using bundle targets.

### Adding a New Repository

1. Create config file:
```bash
cp webapp/configs/ucx.config.yaml webapp/configs/myrepo.config.yaml
```

2. Add target to `databricks.yml`:
```yaml
targets:
  myrepo-dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com/
    variables:
      repo: "myorg/myrepo"
      config_file: "configs/myrepo.config.yaml"
      project_prefix: "myrepo"
      schema: "catalog.schema"
```

3. Use `-t myrepo-dev` flag for all deployment commands

## Troubleshooting

**Vector Search Endpoint Not Found:**
- Create manually: Databricks UI > Compute > Vector Search > Create Endpoint
- Update `databricks.yml` with endpoint name

**Schema Does Not Exist:**
- Ensure schema exists with format `catalog.schema`
- Verify permissions on catalog and schema

**Data Ingestion Fails:**
- GitHub rate limits: Add `--param github_token="your_token"`
- Check workspace has access to Claude Sonnet 4.5

**Permissions Issues:**
- Run `./deploy.sh` to automatically grant required permissions
- Or manually grant via Databricks UI

**Refreshing Knowledge Base:**
```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_token"
```

**Updating Agent:**
```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
```

## Related Links

- [UCX Repository](https://github.com/databrickslabs/ucx)
- [Databricks Apps](https://docs.databricks.com/dev-tools/apps/)
- [Vector Search](https://docs.databricks.com/generative-ai/vector-search.html)
- [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)

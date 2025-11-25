# Codebase Assistant Framework

A framework for building intelligent AI-powered assistants that help users troubleshoot issues and learn how to use any project hosted in GitHub. Powered by Claude Sonnet 4.5 with RAG over codebases, documentation, and internal documents. Pre-configured for UCX and Lakebridge, easily adaptable to other GitHub repositories.

<p align="center">
  <img src="https://github.com/databrickslabs/ucx/raw/main/docs/ucx/static/img/logo.svg" width="200" alt="UCX Logo"><br>
    <b>🚀 Codebase Assistant Framework</b>
</p>

## Currently Supported Repositories
Assistants already available:
- **<a href="https://github.com/databrickslabs/ucx" target="_blank">UCX</a>** – Migrate to Unity Catalog
- **<a href="https://github.com/databrickslabs/lakebridge" target="_blank">Lakebridge</a>** – Migrate from other data platforms to Databricks

## Quick Start

1. Configure deployment settings in `databricks.yml` (or the appropriate target override in `targets/*.yml`) with workspace, vector search endpoint, and schema
2. Deploy resources: `./deploy.sh dev-ucx`
3. (Optional) Upload internal docs (PDF, DOCX, PPTX, images, etc.) to `/Workspace/Shared/ucx` so they are ingested and indexed
4. Run data ingestion: `databricks jobs run-now --job-name "w01_data_ingestion_and_setup" -t dev-ucx --param github_token="your_github_token"`
5. Run agent creation and deployment: `databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-ucx`
6. Customize config (optional): Edit `webapp/configs/ucx.config.yaml`
7. Redeploy with permissions: `./deploy.sh dev-ucx` (after agent endpoint is created)

## Features

### Knowledge Sources
- **Codebase**: Python/SQL code with AI-generated summaries for each function and class
- **Documentation**: README files, user guides, and troubleshooting docs from GitHub
- **Internal Documents**: PDF, DOCX, PPTX, and images uploaded to a workspace folder

### AI Agent
- **MLflow ResponsesAgent** with Claude Sonnet 4.5
- **Vector search retriever tools** for codebase, documentation, and internal documents
- **Source attribution** with links to relevant code and docs

### Multi-Repository Support
- Deploy separate assistants for different repositories using bundle targets
- Shared codebase with per-repository configs, vector indexes, and endpoints

### Audit & Analytics
- **Delta Lake audit logging** for user interactions
- **Admin dashboard** for usage analytics

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

**Data Ingestion (`01_data_ingestion_and_setup/`):**
- Downloads Python/SQL code from GitHub and generates AI summaries
- Ingests documentation and README files
- Creates Delta-synced vector search indexes for both sources

**Agent Deployment (`02_build_agent_and_deploy/`):**
- Defines the agent with vector search retriever tools
- Logs and deploys agent as a model serving endpoint

**Web Application (`webapp/`):**
- Streamlit chat interface with audit integration
- Delta Lake audit logging with privacy management
- Interactive dashboard for analytics and reporting
- Repository-specific configs in `webapp/configs/` (UI text, prompts, etc.)
- Databricks App configs in `webapp/app_configs/` (map targets to config files via `CONFIG_FILE` env var)

## Installation & Deployment

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- Databricks CLI v0.218+ installed and configured
- Workspace administrator privileges
- Access to Claude Sonnet 4.5 foundation model
- Unity Catalog schema with write permissions
- (Optional) GitHub personal access token to avoid API rate limits

### Deployment Steps

#### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd UCX-Troubleshooting-Assistant
```

#### Step 2: Configure databricks.yml and targets
Edit `databricks.yml` and the target files in `targets/*.yml` for each repository you want to support:

- **In `databricks.yml` (root bundle):**
  - **Set required workspace-level variables**:
    - **`vector_search_endpoint`**: Name of the existing Vector Search endpoint.
    - **`catalog_name`** and **`schema_name`**: Combined into `${catalog_name}.${schema_name}` and must point to an existing Unity Catalog catalog and schema.
  - **Keep defaults for app-level variables** (usually not changed globally):
    - **`config_file`**, **`repo`**, **`project_prefix`** and derived variables like `schema`, `volume_name`, `audit_table`, etc.

- **In `targets/*.yml` (per-repository overrides):**
  - For each target (for example `targets/ucx.yml`, `targets/lakebridge.yml`):
    - **Set `workspace.host`** to your Databricks workspace URL.
    - Override **`repo`**, **`config_file`**, and **`project_prefix`** as needed for that repository.
    - Optionally add more targets (e.g., `dev-ucx`, `prod-ucx`, `dev-myrepo`) with their own overrides.

**Note:** Each target can have different repositories, configs, prefixes, and workspaces while sharing the same codebase. See `databricks.yml` and `targets/*.yml` in this repo for complete examples.

#### Step 3: Deploy Resources

Use the `deploy.sh` script to deploy all resources (workflows and app):

```bash
./deploy.sh <target> [profile]

# Examples:
./deploy.sh dev-ucx              # Deploy for dev-ucx target
./deploy.sh dev-lakebridge       # Deploy for dev-lakebridge target  
./deploy.sh dev-ucx myprofile    # With specific Databricks profile
```

**What gets deployed:**
- Two Databricks workflows:
  - `w01_data_ingestion_and_setup` - Ingests code/docs and creates vector indexes
  - `w02_build_agent_and_deploy` - Builds and deploys the MLflow agent
- Streamlit web application

**Note:** 
- Target format must be `<environment>-<project>` (e.g., `dev-ucx`, `prod-lakebridge`)
- Run `./deploy.sh` again after Step 6 to grant serving endpoint permissions

#### Step 4: (Optional) Upload Internal Documents

Upload any internal documents (PDF, DOCX, PPTX, images, etc.) you want indexed to the workspace folder `/Workspace/Shared/{project_prefix}` (for example `/Workspace/Shared/ucx`). The ingestion workflow will copy them into the Unity Catalog volume and index them into an internal documents table and vector store.

#### Step 5: Run Data Ingestion (~30 minutes)

```bash
# With GitHub token (recommended to avoid rate limits)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-ucx --param github_token="your_github_token"

# Without token (may hit rate limits)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" -t dev-ucx

# For specific target
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-myrepo --param github_token="your_github_token"
```

**What it does:**
1. Downloads Python/SQL code from configured GitHub repository
2. Generates AI summaries using Claude Sonnet 4.5
3. Downloads documentation
4. Creates vector indexes: `{schema}.{project_prefix}_codebase_vector` and `{schema}.{project_prefix}_documentation_vector`
5. (Optional) If you upload internal docs (PDF, DOCX, PPTX, images, etc.) to `/Workspace/Shared/{project_prefix}`, they are copied to the Unity Catalog volume and indexed into an internal documents table and vector store.

#### Step 6: Deploy Agent (~5-10 minutes)

```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-ucx

# For specific target
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-myrepo
```

Creates MLflow agent with vector search tools and deploys to model serving endpoint: `agents_{schema}-{project_prefix}_agent`

#### Step 7: Customize Configuration (Optional)

Repository-specific configuration is in `webapp/configs/`. Edit to customize:
- UI text and branding
- Agent system prompt
- Tool descriptions
- Checklists and error messages

Default config is at `webapp/configs/ucx.config.yaml`.

#### Step 8: Grant Endpoint Permissions

After the agent endpoint is deployed (Step 6), run the deploy script again to grant serving endpoint permissions:

```bash
./deploy.sh dev-ucx

# For specific target
./deploy.sh dev-myrepo
```

This grants the app's service principal `CAN QUERY` permission on the serving endpoint.

#### Step 9: Access the Application

Get your app URL:

```bash
databricks apps get dev-ucx-assistant
```

Open the app in your browser and start troubleshooting!

**Access admin dashboard:** 
```
https://your-app-url.databricksapps.com?admin=dashboard
```

**Re-deploying:** If you make changes to the app configuration, simply run `./deploy.sh dev-ucx` again.

## Project Structure

```
UCX-Troubleshooting-Assistant/
├── 01_data_ingestion_and_setup/       # Ingest code/docs, create vector indexes
│   ├── ingest_codebase.py
│   ├── ingest_documentation.py
│   ├── ingest_internal_documents.py
│   ├── setup_document_volume.py
│   └── create_vector.py
│
├── 02_build_agent_and_deploy/         # Build and deploy MLflow agent
│   ├── agent.py
│   └── build_agent_and_deploy.py
│
├── resources/                         # Workflow and app definitions
│   ├── 01_data_ingestion_and_setup.job.yml
│   ├── 02_build_agent_and_deploy.job.yml
│   └── 03_repo_app.yml
│
├── webapp/                            # Streamlit application
│   ├── app.py                         # Main chat interface
│   ├── configs/                       # Repository-specific configurations
│   │   └── ucx.config.yaml           # UCX config (UI, prompts, etc.)
│   ├── app_configs/                   # Databricks Apps configs (per project)
│   │   ├── app.ucx.yaml              # UCX app config (sets CONFIG_FILE, etc.)
│   │   └── app.lakebridge.yaml       # Lakebridge app config
│   ├── audit_*.py                     # Audit system modules
│   ├── model_serving_utils.py         # Model serving interface
│   └── requirements.txt
│
├── targets/                           # Target overrides (per repository)
│   ├── ucx.yml
│   └── lakebridge.yml
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

Deploy separate assistants for different repositories using bundle targets. All assistants share the same codebase, so bug fixes and features apply to all.

### How It Works
- **Shared Code**: All Python code is shared across assistants
- **Separate Resources**: Each assistant gets its own vector indexes, models, endpoints, and audit tables
- **Custom Configuration**: Each repository has its own config file in `webapp/configs/` for UI text, prompts, checklists

### Adding a New Repository

Follow the same deployment steps with these changes:

**Before Step 2:** Create config file
```bash
cp webapp/configs/ucx.config.yaml webapp/configs/myrepo.config.yaml
# Edit myrepo.config.yaml to customize:
# - project_name, ui_title, ui_tagline
# - agent system_prompt
# - checklists and error messages
```

**App config for Databricks Apps:**  
Create `webapp/app_configs/app.myrepo.yaml` based on `webapp/app_configs/app.ucx.yaml` or `app.lakebridge.yaml`, and update:
- `env.CONFIG_FILE` to point to `configs/myrepo.config.yaml`
- (Optional) any extra env vars you need such as `AUDIT_TABLE` or `SERVING_ENDPOINT`

**In Step 2:** Add a new target file under `targets/` (for example `targets/myrepo.yml`) with:
- A `targets:` block containing at least one target such as `dev-myrepo`
- `workspace.host` pointing to your Databricks workspace
- `variables.repo`, `variables.config_file`, and `variables.project_prefix` set for your repository

**In Steps 3-9:** 
- For deployment: `./deploy.sh dev-myrepo` (run in Steps 3 and 8)
- For workflows: Add `-t dev-myrepo` flag to all job commands

### Benefits
- Single codebase for all assistants
- Bug fixes automatically apply everywhere
- Easy to add new repositories
- Complete resource isolation per project
- Customizable UI and prompts per repository

## Usage Examples (UCX)

### Common Questions
- "I'm getting permission errors during UCX installation"
- "How do I run UCX assessment?"
- "How do I migrate external tables?"
- "What's the difference between SYNC and MOVE migration?"

## Troubleshooting

### Common Issues

**Vector Search Endpoint Creation Failed:**
- Create manually: Databricks UI → Compute → Vector Search → Create Endpoint
- Update `databricks.yml` with correct endpoint name

**Schema Does Not Exist:**
- Ensure schema exists with format `catalog.schema` (not `schema.table`)
- Verify you have permissions on both catalog and schema

**Data Ingestion Job Fails (w01):**
- GitHub API rate limits: Use `--param github_token="your_token"`
- Check workspace has access to Claude Sonnet 4.5 endpoint

**App Can't Query Model Endpoint:**
- Ensure you ran `./deploy.sh` again after deploying the agent (Step 8)
- The endpoint must exist before permissions can be granted
- Or manually grant via: Serving → Your endpoint → Permissions

**Audit Logging Fails:**
- Run `./deploy.sh` to automatically grant schema permissions
- Or manually grant Data Editor via: Catalog → Your schema → Permissions

### Refreshing Knowledge Base

Update with latest code/docs:
```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-ucx --param github_token="your_token"
# Agent automatically uses updated indexes, no rebuild needed

# For specific target:
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t dev-myrepo --param github_token="your_token"
```

## Development

### Updating the Agent

After modifying agent configuration or code:
```bash
# Rebuild and redeploy the agent
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-ucx

# For specific target
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t dev-myrepo

# Serving endpoint updates automatically
```

### Updating the App

After modifying the Streamlit app or configuration:
```bash
# Redeploy the app
./deploy.sh dev-ucx

# For specific target
./deploy.sh dev-myrepo
```

## Related Links

- <a href="https://github.com/databrickslabs/ucx" target="_blank">UCX Repository</a>
- <a href="https://databrickslabs.github.io/ucx/" target="_blank">UCX Documentation</a>
- <a href="https://docs.databricks.com/en/dev-tools/databricks-apps/" target="_blank">Databricks Apps</a>
- <a href="https://docs.databricks.com/en/data-governance/unity-catalog/" target="_blank">Unity Catalog</a>
- <a href="https://docs.databricks.com/en/generative-ai/vector-search.html" target="_blank">Vector Search</a>
- <a href="https://docs.databricks.com/en/generative-ai/agent-framework/" target="_blank">Agent Framework</a>

---

**Need help?** Use the app itself to troubleshoot Unity Catalog Migration issues!

# Repository Troubleshooting Assistant

An intelligent AI-powered assistant for troubleshooting repository-specific issues. Built with Streamlit, powered by Claude Sonnet 4.5, and enhanced with vector search over codebases and documentation. Configured by default for Unity Catalog Migration (UCX) but easily adaptable to any GitHub repository.

<p align="center">
  <img src="https://github.com/databrickslabs/ucx/raw/main/docs/ucx/static/img/logo.svg" width="200" alt="UCX Logo"><br>
    <b>🚀 UCX Troubleshooting Assistant</b>
</p>

## Quick Start

1. Configure `databricks.yml` with workspace, vector search endpoint, and schema
2. Deploy resources: `databricks bundle deploy`
3. Run data ingestion: `databricks jobs run-now --job-name "w01_data_ingestion_and_setup"`
4. Deploy agent: `databricks jobs run-now --job-name "w02_build_agent_and_deploy"`
5. Customize config (optional): Edit `webapp/configs/ucx.config.yaml`
6. Deploy app: `./deploy.sh dev-ucx`

## Features

### Intelligent AI Agent with Vector Search
- **Dual Vector Search Indexes**: Queries both codebase and documentation for comprehensive answers
- **Smart Reasoning Process**: Agent explains its thinking and query strategy in real-time
- **Source Attribution**: Provides links to relevant code and documentation
- **Validation-First Approach**: Verifies all functionality exists in the codebase before confirming
- **Multi-Repository Support**: Deploy separate assistants for different repositories using bundle targets

### Knowledge Sources
- **Codebase Index**: Python and SQL code with AI-generated summaries of each function/class
- **Documentation Index**: Chunked README files, user guides, and troubleshooting guides
- **Real-time Updates**: Knowledge base can be refreshed by re-running ingestion workflows

### Advanced AI Capabilities
- **Claude Sonnet 4.5**: State-of-the-art reasoning and code analysis
- **Agentic Framework**: Built using MLflow's ResponsesAgent for robust tool calling
- **Interactive Chat Interface**: Natural language troubleshooting with transparent thinking

### Audit Logging with Delta Lake
- **User Tracking**: Identifies users that interact with the assistant
- **Audit Dashboard**: Real-time analytics for user interactions

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

**Key Variables:**
- **`config_file`**: Path to config within `webapp/configs/` (for UI text, prompts)
- **`repo`**: GitHub repository to ingest in `owner/repo` format
- **`project_prefix`**: Prefix for resources (tables, models, endpoints) - unique per repository
- **`vector_search_endpoint`**: Must exist before deployment (create via Databricks UI: Compute → Vector Search)
- **`schema`**: Must be in `catalog.schema` format with existing catalog and schema

**Note:** Each target can have different repositories, configs, and prefixes while sharing the same codebase.

#### Step 3: Deploy Resources

```bash
# Deploy for default target (ucx-dev)
databricks bundle deploy

# Or specify target explicitly
databricks bundle deploy -t ucx-dev
```

Deploys two workflows (data ingestion + agent deployment) and app configuration for the specified target.

#### Step 4: Run Data Ingestion (~20 minutes)

```bash
# With GitHub token (recommended to avoid rate limits)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_github_token"

# Without token (may hit rate limits)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup"
```

**What it does:**
1. Downloads Python/SQL code from configured GitHub repository
2. Generates AI summaries using Claude Sonnet 4.5
3. Downloads documentation
4. Creates vector indexes: `{schema}.{project_prefix}_codebase_vector` and `{schema}.{project_prefix}_documentation_vector`

#### Step 5: Deploy Agent (~5-10 minutes)

```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
```

Creates MLflow agent with vector search tools and deploys to model serving endpoint: `agents_{schema}-{project_prefix}_agent`

Wait for endpoint to be ready:
```bash
databricks serving-endpoints get --name "agents_{schema}-{project_prefix}_agent"
```

#### Step 6: Customize Configuration (Optional)

Repository-specific configuration is in `webapp/configs/`. Edit to customize:
- UI text and branding
- Agent system prompt
- Tool descriptions
- Checklists and error messages

Default config is at `webapp/configs/ucx.config.yaml`.

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

**In Step 2:** Add your repository target to `databricks.yml`
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

**In Steps 3-7:** Use `-t myrepo-dev` flag for all commands

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
- Run `./deploy.sh` to automatically grant CAN QUERY permission
- Or manually grant via: Serving → Your endpoint → Permissions

**Audit Logging Fails:**
- Run `./deploy.sh` to automatically grant schema permissions
- Or manually grant Data Editor via: Catalog → Your schema → Permissions

### Refreshing Knowledge Base

Update with latest code/docs:
```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_token"
# Agent automatically uses updated indexes, no rebuild needed

# For specific target:
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  -t myrepo-dev --param github_token="your_token"
```

## Development

### Updating the Agent

After modifying agent configuration or code:
```bash
# For default target
databricks jobs run-now --job-name "w02_build_agent_and_deploy"

# For specific target
databricks jobs run-now --job-name "w02_build_agent_and_deploy" -t myrepo-dev

# Serving endpoint updates automatically
```

## Related Links

- [UCX Repository](https://github.com/databrickslabs/ucx)
- [UCX Documentation](https://databrickslabs.github.io/ucx/)
- [Databricks Apps](https://docs.databricks.com/dev-tools/apps/)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)
- [Vector Search](https://docs.databricks.com/generative-ai/vector-search.html)
- [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)

---

**Need help?** Use the app itself to troubleshoot Unity Catalog Migration issues!

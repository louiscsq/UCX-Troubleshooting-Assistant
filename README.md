# 🔧 UCX Troubleshooting Assistant

An intelligent AI-powered assistant for troubleshooting Unity Catalog Migration (UCX) issues. Built with Streamlit, powered by Claude Sonnet 4, and enhanced with vector search over the UCX codebase and documentation for context-aware assistance.

![UCX Logo](https://github.com/databrickslabs/ucx/raw/main/docs/ucx/static/img/ucx.png)

## 🚀 Features

### **🎯 Intelligent AI Agent with Vector Search**
- **Dual Vector Search Indexes**: Queries both UCX codebase and documentation for comprehensive answers
- **Smart Reasoning Process**: Agent explains its thinking and query strategy in real-time
- **Source Attribution**: Provides links to relevant code and documentation
- **Validation-First Approach**: Verifies all functionality exists in the codebase before confirming

### **📚 Knowledge Sources**
- **Codebase Index**: Python and SQL code with AI-generated summaries of each function/class
- **Documentation Index**: Chunked README files, user guides, and troubleshooting guides
- **Real-time Updates**: Knowledge base can be refreshed by re-running ingestion workflows

### **🤖 Advanced AI Capabilities**
- **Claude Sonnet 4.5**: State-of-the-art reasoning and code analysis for summarization
- **Claude Sonnet 4**: Powers the agent for troubleshooting interactions
- **Agentic Framework**: Built using MLflow's ResponsesAgent for robust tool calling
- **Interactive Chat Interface**: Natural language troubleshooting with transparent thinking

### **📊 Audit Logging with Delta Lake**
- **Delta Table Storage**: ACID-compliant audit trails in Unity Catalog
- **User Tracking**: Identifies users via Databricks authentication
- **Privacy Compliance**: Automatic redaction of sensitive information (tokens, keys, passwords)
- **Audit Dashboard**: Real-time analytics with interactive charts, SQL queries, and export capabilities
- **Time Travel**: Query historical versions using Delta Lake features

## 🏗️ Architecture

```
UCX Troubleshooting Assistant
├── Data Ingestion Workflow (w01_data_ingestion_and_setup)
│   ├── Ingest UCX code from GitHub with AI summaries
│   ├── Ingest UCX documentation
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
```

### **Key Components:**

**Data Ingestion (`01_data_ingestion_and_setup/`):**
- Downloads UCX Python/SQL code from GitHub and generates AI summaries
- Ingests UCX documentation and README files
- Creates Delta-synced vector search indexes for both sources

**Agent Deployment (`02_build_agent_and_deploy/`):**
- Defines the agent with vector search retriever tools
- Logs and deploys agent as a model serving endpoint

**Web Application (`webapp/`):**
- Streamlit chat interface with audit integration
- Delta Lake audit logging with privacy management
- Interactive dashboard for analytics and reporting
- All configuration managed via `config.yaml`

## 📦 Installation & Deployment

### **Prerequisites**
- Databricks workspace with Unity Catalog enabled
- Databricks CLI v0.218+ installed and configured
- Workspace administrator privileges
- Access to Claude Sonnet 4.5 and Claude Sonnet 4 foundation models
- Unity Catalog schema with write permissions
- (Optional) GitHub personal access token to avoid API rate limits

### **Quick Deploy**

#### **Step 1: Clone Repository**
```bash
git clone <your-repo-url>
cd UCX-Troubleshooting-Assistant
```

#### **Step 2: Configure databricks.yml**
Edit required variables:
```yaml
variables:
  vector_search_endpoint:
    default: "your_vector_search_endpoint"  # ⚠️ REQUIRED
  
  schema:
    default: "catalog_name.schema_name"  # ⚠️ REQUIRED (format: catalog.schema)

targets:
  dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com/  # ⚠️ UPDATE
```

**Key Requirements:**
- **`vector_search_endpoint`**: Must exist before deployment (create via Databricks UI: Compute → Vector Search)
- **`schema`**: Must be in `catalog.schema` format with existing catalog and schema
- Optional variables (audit_table, table_codebase, etc.) can use default values

#### **Step 3: Deploy Resources**
```bash
databricks bundle deploy
```

Deploys two workflows (data ingestion + agent deployment) and app configuration.

#### **Step 4: Run Data Ingestion (~20 minutes)**
```bash
# With GitHub token (recommended to avoid rate limits)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_github_token"

# Without token (may hit rate limits)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup"
```

**What it does:**
1. Downloads UCX Python/SQL code from GitHub
2. Generates AI summaries using Claude Sonnet 4.5
3. Downloads UCX documentation
4. Creates vector indexes: `{schema}.ucx_codebase_vector` and `{schema}.ucx_documentation_vector`

#### **Step 5: Deploy Agent (~5-10 minutes)**
```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
```

Creates MLflow agent with vector search tools and deploys to model serving endpoint: `agents_{schema}-ucx_agent`

Wait for endpoint to be ready:
```bash
databricks serving-endpoints get --name "agents_{schema}-ucx_agent"
```

#### **Step 6: Configure webapp/config.yaml**
```yaml
deployment:
  serving_endpoint: "agents_main-default-ucx_agent"  # ⚠️ UPDATE with your endpoint name
  audit_table: "catalog.schema.ucx_chat_interactions"  # ⚠️ UPDATE with your table path
  audit_debug: false
```

#### **Step 7: Grant Permissions**
Via Databricks UI, grant to App Service Principal (`{target}-{bundle_name}`, e.g., `dev-ucx-assistant`):
- **Model Endpoint**: Serving → Your endpoint → Permissions → Grant "CAN QUERY"
- **Catalog/Schema**: Catalog → Your schema → Permissions → Grant "Data Editor"

#### **Step 8: Deploy and Start App**
```bash
databricks bundle deploy
databricks bundle run dev-ucx-assistant
```

Get app URL:
```bash
databricks apps get dev-ucx-assistant
```

Access at: `https://dev-ucx-assistant-{workspace-id}.{region}.databricksapps.com`

## 📁 Project Structure

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
│   ├── config.yaml                    # Application configuration
│   ├── audit_*.py                     # Audit system modules
│   ├── model_serving_utils.py         # Model serving interface
│   └── requirements.txt
│
└── databricks.yml                     # Bundle configuration
```

## 📊 Audit & Compliance

### **Interaction Logging**
The assistant includes enterprise-grade audit logging with Delta Lake:

- **User Identity**: Automatically captures user info from Databricks authentication
- **Session Tracking**: Unique session IDs for conversation continuity
- **Interaction Details**: Questions, responses, response times, and error classifications
- **Privacy Protection**: Automatic redaction of sensitive information (tokens, keys, passwords)

### **Configuration**
```yaml
# webapp/config.yaml
deployment:
  audit_table: "catalog.schema.ucx_chat_interactions"
  audit_debug: false
```

### **Audit Schema**
```sql
CREATE TABLE {catalog}.{schema}.ucx_chat_interactions (
  timestamp TIMESTAMP,
  session_id STRING,
  user_email STRING,
  user_question STRING,
  assistant_response STRING,
  response_time_ms INTEGER,
  error_type_detected STRING,
  ...
) USING DELTA
```

### **Audit Dashboard**
**Access via special URL** (hidden from main interface for security):
```
https://your-app-url.databricksapps.com?admin=dashboard
```

**Dashboard Features:**
- 📈 Overview metrics (total interactions, unique users, activity trends)
- ⏰ Timeline analysis with charts (daily/hourly patterns)
- 👥 User patterns and response time analysis
- 🚨 Error tracking and classification
- 📤 Export capabilities (JSON/CSV with date filtering)
- 🔍 Custom SQL queries on audit data

**Example Analytics Query:**
```sql
-- Top users and average response times
SELECT user_email, COUNT(*) as interactions, 
       AVG(response_time_ms) as avg_response_time
FROM {audit_table}
GROUP BY user_email
ORDER BY interactions DESC
LIMIT 10
```

## 🎯 Usage Examples

### **Common Questions**
- "I'm getting permission errors during UCX installation"
- "How do I run UCX assessment?"
- "Assessment job fails to start"
- "How do I migrate external tables?"
- "What's the difference between SYNC and MOVE migration?"
- "Unity Catalog migration not working"

### **Interactive Features**
- 💬 Natural language chat interface with the AI agent
- 🔍 Source links to relevant code and documentation
- 🧠 Transparent thinking process showing agent reasoning
- 📚 View sources used for each answer

## 🔍 Technical Details

### **Vector Search Indexes**
Two specialized indexes powered by Databricks Vector Search:

**Codebase Index** (`{schema}.ucx_codebase_vector`):
- Python and SQL code with AI-generated summaries (Claude Sonnet 4.5)
- Embeddings: `databricks-gte-large-en`
- Use case: Implementation details, feature validation

**Documentation Index** (`{schema}.ucx_documentation_vector`):
- README files, user guides, and troubleshooting docs
- Chunked for optimal retrieval
- Use case: User-facing features, CLI commands, workflows

### **AI Agent Architecture**
- **Framework**: MLflow ResponsesAgent
- **LLM**: Claude Sonnet 4 via Model Serving
- **Tools**: `docs_retriever` (10 results), `codebase_retriever` (8 results)
- **Strategy**: Multi-query iterative retrieval with reasoning (max 20 iterations)

### **Foundation Models**
- **Summarization**: Claude Sonnet 4.5 (`databricks-claude-sonnet-4-5`)
- **Agent**: Claude Sonnet 4 (`databricks-claude-sonnet-4`)
- **Embeddings**: Databricks GTE Large (`databricks-gte-large-en`)

### **Data Pipeline**
1. Code ingestion via Sourcegraph (Python) and GitHub API (SQL)
2. AI summarization using Claude Sonnet 4.5
3. Documentation download and chunking
4. Delta-synced vector index creation with automatic updates

## 🚨 Troubleshooting

### **Common Issues**

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
- Grant CAN QUERY to App Service Principal (`{target}-{bundle_name}`)
- Via: Serving → Your endpoint → Permissions

**Audit Logging Fails:**
- Grant Data Editor permission on catalog/schema to App Service Principal
- Via: Catalog → Your schema → Permissions

### **Refreshing Knowledge Base**
Update with latest UCX code/docs:
```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_token"
# Agent automatically uses updated indexes, no rebuild needed
```

### **Check Vector Search Status**
```python
from databricks.vector_search.client import VectorSearchClient
vsc = VectorSearchClient()
print(vsc.get_index("{schema}.ucx_codebase_vector").describe())
print(vsc.get_index("{schema}.ucx_documentation_vector").describe())
```

## 🔧 Development

### **Local Setup**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
cd webapp
pip install -r requirements.txt
```

Configure `webapp/config.yaml` and set credentials:
```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token"
streamlit run app.py
```

### **Updating the Agent**
After modifying `02_build_agent_and_deploy/agent.py`:
```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
# Serving endpoint updates automatically
```

### **Testing Vector Retrieval**
```python
from databricks.vector_search.client import VectorSearchClient
vsc = VectorSearchClient()
index = vsc.get_index("{schema}.ucx_documentation_vector")
results = index.similarity_search(query="How do I install UCX?", num_results=5)
print(results)
```

## 🔗 Related Links

- [UCX Repository](https://github.com/databrickslabs/ucx)
- [UCX Documentation](https://databrickslabs.github.io/ucx/)
- [Databricks Apps](https://docs.databricks.com/dev-tools/apps/)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)
- [Vector Search](https://docs.databricks.com/generative-ai/vector-search.html)
- [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)

---

**Need help?** Use the app itself to troubleshoot Unity Catalog Migration issues! 🎯


# 🔧 UCX Troubleshooting Assistant

An intelligent AI-powered assistant for troubleshooting Unity Catalog Migration (UCX) issues. Built with Streamlit, powered by Claude Sonnet 4, and enhanced with vector search over the UCX codebase and documentation for context-aware assistance.

![UCX Logo](https://github.com/databrickslabs/ucx/raw/main/docs/ucx/static/img/ucx.png)

## 🚀 Features

### **🎯 Intelligent AI Agent with Vector Search**
- **Dual Vector Search Indexes**: Queries both UCX codebase and documentation for comprehensive answers
- **Smart Reasoning Process**: Agent explains its thinking and query strategy in real-time
- **Source Attribution**: Provides links to relevant code and documentation used to generate answers
- **Multi-Query Strategy**: Automatically queries indexes multiple times as needed for complete answers
- **Validation-First Approach**: Verifies all functionality exists in the codebase before confirming

### **📚 Knowledge Sources**
- **Codebase Index**: Python and SQL code with AI-generated summaries of each function/class
- **Documentation Index**: Chunked README files, user guides, CLI commands, and troubleshooting guides
- **Contextual Retrieval**: Retrieves relevant code snippets and documentation based on user questions
- **Real-time Updates**: Knowledge base can be refreshed by re-running ingestion workflows

### **🤖 Advanced AI Capabilities**
- **Claude Sonnet 4.5 Integration**: State-of-the-art reasoning and code analysis for summarization
- **Claude Sonnet 4**: Powers the agent for troubleshooting interactions
- **Agentic Framework**: Built using MLflow's ResponsesAgent for robust tool calling
- **Interactive Chat Interface**: Natural language troubleshooting conversations
- **Transparent Thinking**: See what the agent is querying and how it's reasoning through problems

### **📊 Comprehensive Audit Logging with Delta Lake**
- **Delta Table Storage**: Scalable ACID-compliant audit trails in Unity Catalog
- **User Tracking**: Identifies users via Databricks authentication headers
- **Interaction Logging**: Records all questions, responses, and metadata
- **Privacy Compliance**: Automatic redaction of sensitive information
- **SQL Analytics**: Custom SQL queries on audit data for advanced analysis
- **Audit Dashboard**: Real-time analytics with interactive charts and reports
- **Export Capabilities**: JSON and CSV export with date range filtering
- **Time Travel**: Query historical versions of audit data using Delta Lake features

## 🏗️ Architecture

```
UCX Troubleshooting Assistant
├── Data Ingestion Workflow (w01_data_ingestion_and_setup)
│   ├── GitHub Code Ingestion (ingest_codebase.py)
│   ├── Documentation Ingestion (ingest_documentation.py)
│   └── Vector Index Creation (create_vector.py)
│       ├── Codebase Vector Index (Python/SQL functions & classes)
│       └── Documentation Vector Index (README chunks)
│
├── Agent Build & Deploy Workflow (w02_build_agent_and_deploy)
│   ├── Agent Model Creation (agent.py)
│   └── Model Serving Deployment (build_agent_and_deploy.py)
│
└── Streamlit Web Application (webapp/)
    ├── Chat Interface (app.py)
    ├── Model Serving Interface (model_serving_utils.py)
    ├── Delta Lake Audit System (audit_utils.py)
    ├── Interactive Dashboard (audit_dashboard.py)
    └── Claude Sonnet 4 + Unity Catalog + Delta Lake
```

### **Core Components:**

**Data Ingestion & Setup (`01_data_ingestion_and_setup/`):**
- **`ingest_codebase.py`**: Downloads UCX Python/SQL code from GitHub, generates AI summaries
- **`ingest_documentation.py`**: Downloads UCX documentation and README files
- **`create_vector.py`**: Creates Delta-synced vector search indexes for both sources

**Agent Build & Deploy (`02_build_agent_and_deploy/`):**
- **`agent.py`**: Defines the ToolCallingAgent with vector search retriever tools
- **`build_agent_and_deploy.py`**: Logs and deploys the agent as a model serving endpoint

**Web Application (`webapp/`):**
- **`app.py`**: Main Streamlit application with chat interface and audit integration
- **`model_serving_utils.py`**: Interface to Databricks model serving endpoints
- **`audit_utils.py`**: Comprehensive audit logging and privacy management with Delta Lake
- **`audit_dashboard.py`**: Interactive dashboard for audit analytics and reporting
- **`config_helper.py`**: Configuration utilities and validation for audit system
- **`admin_utils.py`**: Admin URL generation and secure dashboard access utilities
- **`ucx_utils.py`**: UCX troubleshooting utilities (legacy support)

**Configuration Files:**
- **`databricks.yml`**: Bundle configuration with variables for catalogs, schemas, and endpoints
- **`resources/*.yml`**: Workflow and app resource definitions

## 📦 Installation & Deployment

### **Prerequisites**
- Databricks workspace with Unity Catalog enabled
- Databricks CLI v0.218+ installed and configured
- Workspace administrator privileges
- Access to Claude Sonnet 4.5 and Claude Sonnet 4 foundation models
- **Unity Catalog schema** with write permissions
- (Optional) GitHub personal access token to avoid API rate limits

### **Quick Deploy**

#### **Step 1: Clone the Repository**
```bash
git clone <your-repo-url>
cd UCX-Troubleshooting-Assistant
```

#### **Step 2: Update Configuration**

Edit `databricks.yml` to customize these critical variables:

```yaml
variables:
  vector_search_endpoint:
    description: "Vector Search Endpoint to use for vector search"
    default: "your_vector_search_endpoint"  # ⚠️ REQUIRED: Provide a name (will be created if it doesn't exist)
  
  schema:
    description: "Schema to use for the UCX Assistant"
    default: "catalog_name.schema_name"  # ⚠️ REQUIRED: Use format catalog.schema
  
  # Optional: Update if you want custom table names
  summarising_endpoint:
    description: "Foundational LLM endpoint to use for summarising the codebase"
    default: "databricks-claude-sonnet-4-5"
  
  audit_table:
    description: "Table name for chat interactions logs"
    default: "${var.schema}.ucx_chat_interactions"
  
  table_codebase:
    description: "Table to save codebase information and generate vector store"
    default: "${var.schema}.ucx_codebase"
  
  table_documentation:
    description: "Table to save documentation information and generate vector store"
    default: "${var.schema}.ucx_documentation"
  
  uc_agent_model:
    description: "Model location in Unity Catalog"
    default: "${var.schema}.ucx_agent"

targets:
  dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com/  # ⚠️ UPDATE THIS
```

**Key Configuration Requirements:**
- **`vector_search_endpoint`**: Must exist before deployment. Create via Databricks UI or API
- **`schema`**: Must be in `catalog.schema` format. Ensure catalog and schema exist
- **`host`**: Update to your Databricks workspace URL

#### **Step 3: Deploy Resources**
```bash
databricks bundle deploy
```

This deploys:
- Two Databricks workflows (data ingestion and agent deployment)
- App configuration (not started yet)

#### **Step 4: Run Data Ingestion Workflow**

Run the first workflow to ingest UCX codebase and create vector indexes:

```bash
databricks jobs run-now --job-name "w01_data_ingestion_and_setup"
```

**With GitHub Token (Recommended):**
```bash
# Generate a token at https://github.com/settings/tokens (no special permissions needed for public repos)
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_github_token"
```

**⏱️ Expected Runtime:** ~20 minutes (due to AI summarization of code)

**What This Does:**
1. Downloads UCX Python and SQL code from GitHub
2. Generates AI summaries of each function/class using Claude Sonnet 4.5
3. Downloads UCX documentation and README files
4. Creates two vector search indexes:
   - `{schema}.ucx_codebase_vector` (code with summaries)
   - `{schema}.ucx_documentation_vector` (documentation chunks)

#### **Step 5: Build and Deploy Agent**

Run the second workflow to build the AI agent and deploy it:

```bash
databricks jobs run-now --job-name "w02_build_agent_and_deploy"
```

**⏱️ Expected Runtime:** ~5-10 minutes

**What This Does:**
1. Creates an MLflow agent with vector search retriever tools
2. Logs the agent to Unity Catalog at `{schema}.ucx_agent`
3. Deploys the agent as a model serving endpoint
4. Endpoint name: `agents_{schema}-ucx_agent` (e.g., `agents_main-default-ucx_agent`)

**Wait for Endpoint:** Monitor the serving endpoint until status shows "Running":
```bash
databricks serving-endpoints get --name "agents_{schema}-ucx_agent"
```

#### **Step 6: Configure Web Application**

Edit `webapp/app.yaml` with your specific values:

```yaml
command: ["streamlit", "run", "app.py"]

env:
  - name: STREAMLIT_BROWSER_GATHER_USAGE_STATS
    value: "false"
  
  - name: "SERVING_ENDPOINT"
    value: "agents_your-schema-ucx_agent"  # ⚠️ UPDATE: Your agent endpoint name
  
  - name: "AUDIT_TABLE"
    value: "catalog.schema.ucx_chat_interactions"  # ⚠️ UPDATE: Full path to audit table
  
  - name: "AUDIT_DEBUG"
    value: "false"
```

#### **Step 7: Grant Permissions**

The app needs permissions to query the model and write audit logs:

**Grant Model Endpoint Query Permission:**
```bash
# Via Databricks UI:
# 1. Go to Serving → Your endpoint (agents_{schema}-ucx_agent)
# 2. Click "Permissions"
# 3. Grant "CAN QUERY" to the App Service Principal
```

**Grant Unity Catalog Write Permission:**
```bash
# Via Databricks UI:
# 1. Go to Catalog → Your catalog → Your schema
# 2. Click "Permissions"
# 3. Grant "Data Editor" permissions to the App Service Principal
```

The App Service Principal name format: `{target}-{bundle_name}` (e.g., `dev-ucx-assistant`)

#### **Step 8: Redeploy and Start App**

```bash
# Redeploy with updated app.yaml
databricks bundle deploy

# Start the app
databricks apps start dev-ucx-assistant
```

#### **Step 9: Access Your App**

Get the app URL:
```bash
databricks apps get dev-ucx-assistant
```

The URL format: `https://dev-ucx-assistant-{workspace-id}.{region}.databricksapps.com`

## 📁 Project Structure

```
UCX-Troubleshooting-Assistant/
├── 01_data_ingestion_and_setup/
│   ├── create_vector.py              # Creates vector search indexes
│   ├── ingest_codebase.py            # Ingests UCX Python/SQL code
│   └── ingest_documentation.py       # Ingests UCX documentation
│
├── 02_build_agent_and_deploy/
│   ├── agent.py                      # Agent definition with vector search tools
│   └── build_agent_and_deploy.py    # Builds and deploys agent to model serving
│
├── resources/
│   ├── 01_data_ingestion_and_setup.job.yml   # Data ingestion workflow definition
│   ├── 02_build_agent_and_deploy.job.yml     # Agent deployment workflow definition
│   └── app_assistant.app.yml                 # Streamlit app resource definition
│
├── webapp/                           # Web application code
│   ├── app.py                        # Main Streamlit application
│   ├── app.yaml                      # App runtime configuration
│   ├── model_serving_utils.py        # Model serving interface
│   ├── audit_utils.py                # Delta Lake audit system
│   ├── audit_dashboard.py            # Interactive audit dashboard
│   ├── audit_diagnostics.py          # Audit diagnostics utilities
│   ├── config_helper.py              # Configuration validation
│   ├── admin_utils.py                # Admin URL generation
│   ├── messages.py                   # Message rendering utilities
│   ├── simple_audit_utils.py         # Simple audit utilities
│   ├── spark_diagnostics.py          # Spark diagnostics
│   ├── sql_audit_utils.py            # SQL audit utilities
│   ├── ucx_utils.py                  # UCX troubleshooting utilities
│   └── requirements.txt              # Python dependencies
│
├── databricks.yml                    # Databricks bundle configuration
├── README.md                         # This file
└── AUDIT_CONFIG_EXAMPLES.md          # Audit configuration examples
```

## 📊 Audit & Compliance Features

### **Comprehensive Interaction Logging**

The UCX troubleshooting assistant includes enterprise-grade audit logging that tracks:

- **User Identity**: Automatically captures user information from Databricks authentication
- **Session Tracking**: Unique session IDs for conversation continuity
- **Interaction Details**: Questions, responses, response times, and error classifications
- **Privacy Protection**: Automatic redaction of sensitive information (tokens, keys, passwords)
- **Compliance Ready**: Structured logging for audit trails and compliance reporting

### **🔧 Configurable Audit Storage**

The audit system uses **Delta Lake tables** in Unity Catalog for enterprise-grade data management:

#### **Environment Variables Configuration**
```bash
# Configure audit table location in webapp/app.yaml
export AUDIT_TABLE="catalog.schema.table_name"
```

#### **Databricks Bundle Configuration**
In `databricks.yml`:
```yaml
variables:
  audit_table:
    description: "Table name for chat interactions logs in catalog.schema.table format"
    default: "${var.schema}.ucx_chat_interactions"
```

### **Audit Data Schema**

The Delta table uses this optimized schema:
```sql
CREATE TABLE {catalog}.{schema}.ucx_chat_interactions (
  timestamp TIMESTAMP NOT NULL,
  session_id STRING NOT NULL,
  user_name STRING,
  user_email STRING,
  user_id STRING,
  user_question STRING NOT NULL,
  assistant_response STRING NOT NULL,
  ucx_context_used BOOLEAN NOT NULL,
  error_type_detected STRING,
  response_time_ms INTEGER NOT NULL,
  endpoint_used STRING NOT NULL,
  interaction_type STRING NOT NULL
) USING DELTA
TBLPROPERTIES (
  'description' = 'UCX Troubleshooting Assistant Audit Log',
  'created_by' = 'UCX-Troubleshooting-Assistant'
)
```

### **SQL Query Examples**

Access powerful analytics through the dashboard's SQL interface:

```sql
-- Top 10 most active users
SELECT user_email, COUNT(*) as interactions, 
       AVG(response_time_ms) as avg_response_time
FROM {audit_table}
WHERE user_email IS NOT NULL
GROUP BY user_email
ORDER BY interactions DESC
LIMIT 10
```

```sql
-- Daily usage trends (last 30 days)
SELECT DATE(timestamp) as date, 
       COUNT(*) as interactions,
       COUNT(DISTINCT user_email) as unique_users
FROM {audit_table}
WHERE timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY DATE(timestamp)
ORDER BY date DESC
```

### **Audit Dashboard Features**

The audit dashboard is **hidden from the main interface** for security and is accessible only via a special URL.

#### **🔒 Secure Admin Access**

**Admin URL Format:**
```
https://your-app-url.databricksapps.com?admin=dashboard
```

**Example Admin URLs:**
```bash
# Development Environment
https://dev-ucx-assistant-{workspace-id}.1.azure.databricksapps.com?admin=dashboard

# Production Environment  
https://prod-ucx-assistant-{workspace-id}.1.azure.databricksapps.com?admin=dashboard
```

#### **🛡️ Security Features**
- **Hidden Access**: Dashboard not visible in main app interface
- **URL-Based Authentication**: Requires special query parameter 
- **Databricks Authentication**: Uses existing workspace authentication
- **Access Logging**: All admin dashboard access is logged for audit trails

#### **📊 Dashboard Capabilities**

- **📈 Overview Metrics**: Total interactions, unique users, last activity
- **⏰ Timeline Analysis**: Daily and hourly interaction patterns with charts
- **👥 User Patterns**: Interaction types, response time analysis, usage trends
- **🚨 Error Analysis**: Common error patterns and frequency tracking
- **💬 Recent Interactions**: Filterable list of recent conversations
- **📤 Export Capabilities**: JSON and CSV export with date range filtering
- **🔍 SQL Analytics**: Run custom SQL queries directly on the audit table

## 🎯 Usage Examples

### **Common Use Cases**

1. **Installation Issues**:
   - "I'm getting permission errors during UCX installation"
   - "How do I install UCX on Azure Databricks?"
   - "What are the prerequisites for UCX?"

2. **Assessment Problems**:
   - "Assessment job fails to start"
   - "How do I run UCX assessment?"
   - "What does the assessment report show?"

3. **Migration Errors**:
   - "Unity Catalog migration not working"
   - "How do I migrate external tables?"
   - "What's the difference between SYNC and MOVE migration?"

### **Interactive Features**

- **💬 Chat Interface**: Natural language troubleshooting with the AI agent
- **🔍 Source Links**: Click through to relevant code and documentation
- **🧠 Thinking Process**: See how the agent queries the knowledge base
- **📚 Transparent Retrieval**: View what sources were used for each answer

## 🔍 Technical Details

### **Vector Search Implementation**

The assistant uses Databricks Vector Search with two specialized indexes:

**Codebase Index (`{schema}.ucx_codebase_vector`):**
- **Content**: Python and SQL code from the UCX repository
- **Processing**: AI-generated summaries of each function and class using Claude Sonnet 4.5
- **Embeddings**: Generated using `databricks-gte-large-en` model
- **Use Case**: Understanding implementation details, validating features exist

**Documentation Index (`{schema}.ucx_documentation_vector`):**
- **Content**: README files, user guides, and documentation
- **Processing**: Chunked for optimal retrieval
- **Embeddings**: Generated using `databricks-gte-large-en` model
- **Use Case**: Understanding user-facing features, CLI commands, workflows

### **AI Agent Architecture**

- **Framework**: MLflow ResponsesAgent (Responses API compatible)
- **LLM**: Claude Sonnet 4 via Databricks Model Serving
- **Tools**: 
  - `docs_retriever`: Queries documentation vector index (10 results)
  - `codebase_retriever`: Queries codebase vector index (8 results)
- **Strategy**: Multi-query iterative retrieval with reasoning
- **Max Iterations**: 20 tool calls to find comprehensive answers

### **Foundation Models**

- **Summarization**: Claude Sonnet 4.5 by Anthropic (`databricks-claude-sonnet-4-5`)
- **Agent**: Claude Sonnet 4 by Anthropic (`databricks-claude-sonnet-4`)
- **Embeddings**: Databricks GTE Large English (`databricks-gte-large-en`)

### **Data Ingestion Pipeline**

1. **Code Ingestion**: Uses Sourcegraph to parse Python code and GitHub API for SQL
2. **AI Summarization**: Each function/class summarized using Claude Sonnet 4.5
3. **Documentation Ingestion**: README files downloaded and chunked
4. **Vector Index Creation**: Delta-synced indexes with automatic updates

## 🚨 Troubleshooting

### **Common Deployment Issues**

1. **Vector Search Endpoint Creation Failed**:
   ```bash
   # The endpoint should be created automatically during Step 4
   # If creation fails, you can create one manually:
   # Via Databricks UI: Compute → Vector Search → Create Endpoint
   # Then ensure databricks.yml references the correct endpoint name
   ```

2. **Schema Does Not Exist**:
   ```bash
   # Ensure schema exists and you have permissions
   # Format must be catalog.schema (not schema.table)
   ```

3. **Workflow w01_data_ingestion_and_setup Fails**:
   ```bash
   # Check GitHub API rate limits
   # Run with github_token parameter to avoid throttling:
   databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
     --param github_token="your_token"
   ```

4. **App Can't Query Model Endpoint**:
   ```bash
   # Grant CAN QUERY permission to App Service Principal
   # Go to Serving → Endpoint → Permissions
   # Add: {target}-{bundle_name} with CAN QUERY
   ```

5. **Audit Logging Fails**:
   ```bash
   # Grant Data Editor permission on catalog.schema
   # Go to Catalog → Your Schema → Permissions
   # Add: {target}-{bundle_name} with Data Editor role
   ```

### **Refreshing the Knowledge Base**

To update with the latest UCX code and documentation:

```bash
# Re-run data ingestion workflow
databricks jobs run-now --job-name "w01_data_ingestion_and_setup" \
  --param github_token="your_token"

# No need to rebuild agent - it automatically uses updated indexes
```

### **Checking Vector Search Status**

```python
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# Check indexes
codebase_index = vsc.get_index("{schema}.ucx_codebase_vector")
docs_index = vsc.get_index("{schema}.ucx_documentation_vector")

print(codebase_index.describe())
print(docs_index.describe())
```

## 🔧 Development

### **Local Development Setup**

1. **Set up Python environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   cd webapp
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   ```bash
   export SERVING_ENDPOINT="agents_your-schema-ucx_agent"
   export AUDIT_TABLE="catalog.schema.ucx_chat_interactions"
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   export DATABRICKS_TOKEN="your-token"
   ```

3. **Run locally** (requires Databricks authentication):
   ```bash
   streamlit run app.py
   ```

### **Updating the Agent**

After modifying `02_build_agent_and_deploy/agent.py`:

```bash
# Re-run the build workflow
databricks jobs run-now --job-name "w02_build_agent_and_deploy"

# The serving endpoint will automatically update
```

### **Testing Vector Search Retrieval**

```python
from databricks_openai import VectorSearchRetrieverTool

tool = VectorSearchRetrieverTool(
    index_name="{schema}.ucx_documentation_vector",
    tool_name="test_retriever",
    doc_uri="file_url",
    num_results=5
)

results = tool.execute(query="How do I install UCX?")
print(results)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test deployment locally or in dev workspace
5. Submit a pull request

## 📄 License

This project is licensed under the same terms as UCX - see the [UCX License](https://github.com/databrickslabs/ucx/blob/main/LICENSE) for details.

## 🔗 Related Links

- **UCX Repository**: https://github.com/databrickslabs/ucx
- **UCX Documentation**: https://databrickslabs.github.io/ucx/
- **Databricks Apps**: https://docs.databricks.com/dev-tools/apps/
- **Unity Catalog**: https://docs.databricks.com/data-governance/unity-catalog/
- **Vector Search**: https://docs.databricks.com/generative-ai/vector-search.html
- **Agent Framework**: https://docs.databricks.com/generative-ai/agent-framework/

---

**Need help?** Use the app itself! It's designed to troubleshoot Unity Catalog Migration issues, including questions about this deployment. 🎯

**App URL**: `https://dev-ucx-assistant-{workspace-id}.{region}.databricksapps.com`
```

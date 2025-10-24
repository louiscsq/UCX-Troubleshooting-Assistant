# 🔧 UCX Troubleshooting Assistant

A Databricks application that provides intelligent troubleshooting assistance for Unity Catalog Migration (UCX) issues. Built with Streamlit and powered by Claude Sonnet 4, this app includes a cached version of the official UCX codebase for enhanced analysis and support.

![UCX Logo](https://github.com/databrickslabs/ucx/raw/main/docs/ucx/static/img/ucx.png)

## 🚀 Features

### **🎯 Intelligent Troubleshooting**
- **Smart Error Analysis**: Analyzes error messages and matches them with known UCX patterns
- **Source Code Integration**: Scans 100+ UCX Python files for relevant error handling patterns
- **Live Documentation**: Accesses official UCX documentation and troubleshooting guides
- **Contextual Responses**: Provides targeted solutions based on actual UCX codebase

### **📋 Built-in Checklists**
- **Installation Checklist**: 8-step verification process for UCX setup
- **Assessment Checklist**: 7-step guide for running UCX assessments
- **Common Errors**: Pre-defined solutions for 7+ common UCX error types

### **🤖 AI-Powered Assistance**
- **Claude Sonnet 4 Integration**: State-of-the-art reasoning and code analysis
- **Chat Interface**: Interactive troubleshooting conversations
- **Multi-mode Support**: Both instant responses and extended reasoning

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
UCX Troubleshooting App
├── Streamlit Frontend (app.py)
├── UCX Knowledge Engine (ucx_utils.py)
├── Model Serving Interface (model_serving_utils.py)
├── Delta Lake Audit System (audit_utils.py)
├── Interactive Dashboard (audit_dashboard.py)
├── Cached UCX Codebase (ucx-codebase/)
└── Claude Sonnet 4 + Unity Catalog + Delta Lake
```

### **Core Components:**

- **`app.py`**: Main Streamlit application with chat interface and audit integration
- **`ucx_utils.py`**: UCX troubleshooting utilities and codebase analysis
- **`model_serving_utils.py`**: Interface to Databricks model serving endpoints
- **`audit_utils.py`**: Comprehensive audit logging and privacy management with Delta Lake
- **`audit_dashboard.py`**: Interactive dashboard for audit analytics and reporting
- **`config_helper.py`**: Configuration utilities and validation for audit system
- **`admin_utils.py`**: Admin URL generation and secure dashboard access utilities
- **`ucx-codebase/`**: Cached copy of the official UCX repository from [databrickslabs/ucx](https://github.com/databrickslabs/ucx)

## 📦 Installation & Deployment

### **Prerequisites**
- Databricks workspace with Unity Catalog enabled
- Databricks CLI v0.218+ installed and configured
- Workspace administrator privileges
- Access to Claude Sonnet 4 foundation model

### **Quick Deploy**

1. **Clone this repository**:
   ```bash
   git clone <your-repo-url>
   cd ucx-troubleshooting-app
   ```

2. **Update configuration**:
   Edit `databricks.yaml`:
   ```yaml
   variables:
      vector_search_endpoint: "<your_vector_search_endpoint>"
      schema: "catalog.schema"      # Must exist and be writable
      host: "https://<your-workspace>.cloud.databricks.com"
   ```


3. **Deploy to Databricks**:
   ```bash
   databricks bundle validate
   databricks bundle deploy --target dev
   ```

4. **Run data ingestion workflow**
   ```bash
   databricks workflow run w01_data_ingestion_and_setup   --param github_token=<your_github_token>
   ```
   > Optional but recommended: prevents GitHub API throttling.


5. Update `webapp/app.yaml`:
   ```yaml
   env:
   - name: SERVING_ENDPOINT
      value: "<your_serving_endpoint_name>"
   - name: AUDIT_TABLE
      value: "<catalog.schema.audit_table>"
   ```

6. **Grant Permissions**
   | Resource | Permission | Purpose |
   |-----------|-------------|----------|
   | Model Serving Endpoint | `CAN QUERY` | Allow app to invoke the model |
   | Catalog/Schema | `Data Editor` | Allow app to write audit data |


   Then redeploy:
   ```bash
   databricks bundle deploy
   ```

7. **Launch the App**
   ```bash
   databricks bundle run <appname>
   ```


## 📁 Project Structure

```
ucx-troubleshooting-app/
├── app.py                      # Main Streamlit application
├── ucx_utils.py               # UCX troubleshooting utilities
├── model_serving_utils.py     # Model serving interface
├── audit_utils.py             # Delta Lake audit system
├── audit_dashboard.py         # Interactive audit dashboard
├── config_helper.py           # Configuration utilities  
├── admin_utils.py             # Admin URL generation and secure access
│
├── requirements.txt           # Python dependencies
├── databricks.yml             # Databricks bundle configuration (with audit variables)
├── app.yaml                   # App runtime configuration (with audit env vars)
├── .databricksignore          # Files to exclude from deployment
├── .gitignore                 # Git ignore patterns
├── .dockerignore              # Docker ignore patterns
├── AUDIT_CONFIG_EXAMPLES.md   # Configuration examples and best practices
│
└── ucx-codebase/              # Cached UCX repository
    ├── src/                   # UCX source code
    ├── docs/                  # UCX documentation
    ├── tests/                 # UCX tests (filtered)
    └── README.md              # UCX official README
```

## 📊 Audit & Compliance Features

### **Comprehensive Interaction Logging**

The UCX troubleshooting app includes enterprise-grade audit logging that tracks:

- **User Identity**: Automatically captures user information from Databricks authentication
- **Session Tracking**: Unique session IDs for conversation continuity
- **Interaction Details**: Questions, responses, response times, and error classifications
- **Privacy Protection**: Automatic redaction of sensitive information (tokens, keys, passwords)
- **Compliance Ready**: Structured logging for audit trails and compliance reporting

### **🔧 Configurable Audit Storage**

The audit system supports **fully configurable** Delta table locations:

#### **Environment Variables Configuration**
```bash
# Configure audit table location
export AUDIT_CATALOG="your_catalog"        # Default: "main"
export AUDIT_SCHEMA="your_schema"          # Default: "ucx_audit" 
export AUDIT_TABLE="your_table_name"       # Default: "chat_interactions"
```

#### **Databricks Bundle Configuration**
In `databricks.yml`, customize per environment:
```yaml
variables:
  audit_catalog:
    description: "Unity Catalog name for audit tables"
    default: "main"
  audit_schema:
    description: "Schema name for audit tables"
    default: "ucx_audit"

targets:
  dev:
    variables:
      audit_catalog: "main"
      audit_schema: "ucx_audit_dev"
      
  prod:
    variables:
      audit_catalog: "shared"
      audit_schema: "ucx_audit_prod"
```

#### **Environment-Specific Examples**

**Development Environment:**
- Table: `main.ucx_audit_dev.chat_interactions`
- Isolated from production data
- Can be freely reset/modified

**Production Environment:**
- Table: `shared.ucx_audit_prod.chat_interactions`
- Centralized location for enterprise reporting
- Strict access controls and retention policies

**Multi-Tenant Setup:**
- Table: `tenant_a.ucx_audit.chat_interactions`
- Separate audit trails per tenant/organization
- Independent data governance

#### **Configuration Validation**

The app automatically validates configuration and displays helpful information:

```python
# In your app, configuration is auto-validated
from config_helper import AuditConfig

config = AuditConfig.get_config()
validation = AuditConfig.validate_config()

# View in dashboard: Shows current table location and any issues
```

### **🚀 Quick Deployment Examples**

#### **Standard Deployment (Development)**
```bash
# Use default settings (main.ucx_audit_dev.chat_interactions)
databricks bundle deploy --target dev
```

#### **Production Deployment with Custom Catalog**
```bash
# Edit databricks.yml first to set production values
databricks bundle deploy --target prod

# Or override with environment variables
export AUDIT_CATALOG="enterprise_catalog"
export AUDIT_SCHEMA="compliance_audit"
databricks bundle deploy --target prod
```

#### **Multi-Environment Setup**
```bash
# Development
AUDIT_SCHEMA="ucx_dev" databricks bundle deploy --target dev

# Staging  
AUDIT_SCHEMA="ucx_staging" databricks bundle deploy --target staging

# Production
AUDIT_CATALOG="shared" AUDIT_SCHEMA="ucx_prod" databricks bundle deploy --target prod
```

#### **Organization-Specific Deployment**
```bash
# For specific business unit or team
export AUDIT_CATALOG="sales_analytics"
export AUDIT_SCHEMA="ucx_troubleshooting"
databricks bundle deploy --target prod
```

The audit system now uses **Delta Lake tables** for enterprise-grade data management:

#### **🏛️ Delta Table Architecture**
- **Location**: `main.ucx_audit.chat_interactions` (configurable)
- **Schema**: Structured schema with proper data types and constraints
- **ACID Compliance**: Guaranteed data consistency and reliability
- **Versioning**: Complete audit trail with time travel capabilities
- **Auto-Partitioning**: Optimized for time-based queries

#### **📊 Advanced Analytics**
- **SQL Interface**: Direct SQL querying in the audit dashboard
- **Predefined Queries**: User activity, daily trends, error analysis, performance metrics
- **Custom Analytics**: Write your own SQL queries for specific insights
- **Interactive Charts**: Automatic visualization of query results
- **Export Integration**: CSV downloads directly from SQL query results

#### **🔄 Dual-Mode Operation**
- **Primary**: Delta Lake tables for production deployments
- **Fallback**: JSON files when Delta/Spark unavailable (local development)
- **Seamless Switching**: Automatic detection and graceful degradation
- **Migration Path**: Easy upgrade from JSON to Delta Lake storage

### **Audit Data Schema**

The Delta table uses this optimized schema:
```sql
CREATE TABLE main.ucx_audit.chat_interactions (
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
FROM {table_name}
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
FROM {table_name}
WHERE timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY DATE(timestamp)
ORDER BY date DESC
```

```sql
-- Error pattern analysis
SELECT error_type_detected, COUNT(*) as frequency,
       AVG(response_time_ms) as avg_response_time
FROM {table_name}
WHERE error_type_detected IS NOT NULL
GROUP BY error_type_detected
ORDER BY frequency DESC
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
https://dev-ucx-doctor-{workspace-id}.1.azure.databricksapps.com?admin=dashboard

# Production Environment  
https://prod-ucx-doctor-{workspace-id}.1.azure.databricksapps.com?admin=dashboard
```

#### **🛡️ Security Features**
- **Hidden Access**: Dashboard not visible in main app interface
- **URL-Based Authentication**: Requires special query parameter 
- **Databricks Authentication**: Uses existing workspace authentication
- **Access Logging**: All admin dashboard access is logged for audit trails
- **User Identification**: Admins identified via Databricks headers

#### **📊 Dashboard Capabilities**

Access the dashboard via the admin URL to get:

- **📈 Overview Metrics**: Total interactions, unique users, file sizes, last activity
- **⏰ Timeline Analysis**: Daily and hourly interaction patterns with charts
- **👥 User Patterns**: Interaction types, response time analysis, usage trends
- **🚨 Error Analysis**: Common error patterns and frequency tracking
- **💬 Recent Interactions**: Filterable list of recent conversations
- **📤 Export Capabilities**: JSON and CSV export with date range filtering

## 🔐 Admin Dashboard Access

### **Secure URL-Based Access**

The audit dashboard is **hidden from the main app interface** and accessible only via a special admin URL for enhanced security.

#### **🎯 How to Access**

**Step 1**: Get your app's base URL after deployment
```bash
databricks apps get dev-ucx-doctor
# Output will show: "url": "https://dev-ucx-doctor-{workspace-id}.1.azure.databricksapps.com"
```

**Step 2**: Add the admin query parameter
```
https://your-app-url?admin=dashboard
```

**Step 3**: Access the admin dashboard
- Visit the admin URL in your browser
- Dashboard will load instead of the normal chat interface
- All standard Databricks workspace authentication applies

#### **🔒 Security Benefits**
- **No Visible Access**: Regular users cannot see or access the dashboard
- **URL-Based Gate**: Only administrators with the special URL can access
- **Audit Trail**: All admin access attempts are logged with user identification
- **Databricks Auth**: Uses workspace authentication (no additional login required)

#### **💡 Usage Tips**
- **Bookmark** the admin URL for easy access
- **Share securely** only with authorized team members
- **Monitor access** via the audit logs in the dashboard itself

### **Admin Dashboard Features**

Once accessed via the admin URL, you get access to:

- **Automatic Redaction**: Sensitive tokens, keys, and passwords are automatically redacted
- **Anonymization Options**: User data can be hashed for additional privacy
- **Local Storage**: Audit logs stored locally in `audit_logs/` directory
- **Secure Headers**: Uses Databricks authentication headers for user identification
- **No External Dependencies**: All audit data stays within your Databricks environment

### **Compliance Benefits**

- **Audit Trail**: Complete record of all troubleshooting interactions
- **User Accountability**: Track who accessed the system and when
- **Usage Analytics**: Understand common issues and system usage patterns  
- **Performance Monitoring**: Response time tracking and optimization insights
- **Error Trending**: Identify recurring issues for proactive resolution

## 🔧 Development

1. **Set up Python environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Update UCX codebase cache**:
   ```bash
   rm -rf ucx-codebase/
   git clone https://github.com/databrickslabs/ucx.git ucx-codebase
   rm -rf ucx-codebase/tests/unit/source_code/samples/functional/
   ```

3. **Run locally** (requires Databricks authentication):
   ```bash
   export SERVING_ENDPOINT="databricks-claude-sonnet-4"
   streamlit run app.py
   ```

### **Updating Dependencies**

```bash
pip install <new-package>
pip freeze > requirements.txt
```

## 🎯 Usage Examples

### **Common Use Cases**

1. **Installation Issues**:
   - "I'm getting permission errors during UCX installation"
   - "Python version compatibility problems"
   - "Databricks CLI issues"

2. **Assessment Problems**:
   - "Assessment job fails to start"
   - "Cannot connect to external Hive Metastore"
   - "Authentication failures during assessment"

3. **Migration Errors**:
   - "Unity Catalog migration not working"
   - "Table migration failures"
   - "External location issues"

### **Interactive Features**

- **📋 Installation Checklist**: Quick access via sidebar
- **🔍 Assessment Checklist**: Step-by-step verification
- **🚨 Common Errors**: Pre-defined solutions for known issues
- **💬 Chat Interface**: Natural language troubleshooting

## 🔍 Technical Details

### **UCX Codebase Integration**

The app includes a cached version of the UCX repository that enables:

- **Pattern Recognition**: Scans Python files for error patterns
- **Documentation Access**: Loads official troubleshooting guides
- **Source Analysis**: Matches user issues with actual UCX code
- **Smart Context**: Provides Claude Sonnet 4 with real UCX expertise

### **Foundation Model**

- **Model**: Claude Sonnet 4 by Anthropic
- **Endpoint**: `databricks-claude-sonnet-4`
- **Features**: Hybrid reasoning, code analysis, technical troubleshooting
- **Context Window**: Large enough for UCX documentation and code analysis

### **Error Analysis Engine**

Automatically detects and categorizes:
- Authentication errors
- Permission issues  
- Hive Metastore problems
- Cluster configuration issues
- Unity Catalog problems
- Python version conflicts
- CLI issues

## 🚨 Troubleshooting

### **Common Deployment Issues**

1. **Bundle validation fails**:
   ```bash
   # Check workspace URL in databricks.yml
   databricks workspace current
   ```

2. **App won't start**:
   ```bash
   # Check app status
   databricks apps get dev-ucx-doctor
   
   # Restart if needed
   databricks apps start dev-ucx-doctor
   ```

3. **Missing UCX codebase**:
   ```bash
   # Re-clone UCX repository
   rm -rf ucx-codebase/
   git clone https://github.com/databrickslabs/ucx.git ucx-codebase
   rm -rf ucx-codebase/tests/unit/source_code/samples/functional/
   ```

### **File Size Issues**

If you encounter "file too large" errors:
- The `.databricksignore` excludes large files
- UCX `.git` directory is excluded
- Problematic test files are filtered out

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test deployment locally
5. Submit a pull request

## 📄 License

This project is licensed under the same terms as UCX - see the [UCX License](https://github.com/databrickslabs/ucx/blob/main/LICENSE) for details.

## 🔗 Related Links

- **UCX Repository**: https://github.com/databrickslabs/ucx
- **UCX Documentation**: https://databrickslabs.github.io/ucx/
- **Databricks Apps**: https://docs.databricks.com/dev-tools/apps/
- **Unity Catalog**: https://docs.databricks.com/data-governance/unity-catalog/

---

**Need help?** Use the app itself! It's designed to troubleshoot Unity Catalog Migration issues, including problems with this troubleshooting app. 🎯

**App URL**: `https://dev-ucx-doctor-{workspace-id}.{region}.databricksapps.com`

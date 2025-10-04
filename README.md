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

## 🏗️ Architecture

```
UCX Troubleshooting App
├── Streamlit Frontend (app.py)
├── UCX Knowledge Engine (ucx_utils.py)
├── Model Serving Interface (model_serving_utils.py)
├── Cached UCX Codebase (ucx-codebase/)
└── Claude Sonnet 4 Foundation Model
```

### **Core Components:**

- **`app.py`**: Main Streamlit application with chat interface
- **`ucx_utils.py`**: UCX troubleshooting utilities and codebase analysis
- **`model_serving_utils.py`**: Interface to Databricks model serving endpoints
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
   ```bash
   # Edit databricks.yml - update workspace host
   vim databricks.yml
   ```

3. **Deploy to Databricks**:
   ```bash
   databricks bundle validate
   databricks bundle deploy --target dev
   ```

4. **Start the app**:
   ```bash
   databricks apps start dev-ucx-doctor
   ```

### **Configuration Files**

#### **`databricks.yml`** - Bundle Configuration
```yaml
bundle:
  name: ucx-doctor

workspace:
  host: https://your-workspace.cloud.databricks.com  # Update this

resources:
  apps:
    ucx_doctor_app:
      name: ${bundle.target}-${bundle.name}
      description: "UCX Troubleshooting Assistant"
      source_code_path: ./
```

#### **`app.yaml`** - App Configuration  
```yaml
command: ["streamlit", "run", "app.py"]

env:
  - name: STREAMLIT_BROWSER_GATHER_USAGE_STATS
    value: "false"
  - name: "SERVING_ENDPOINT"
    value: "databricks-claude-sonnet-4"  # Foundation model endpoint
```

## 📁 Project Structure

```
ucx-troubleshooting-app/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── databricks.yml              # Databricks bundle configuration
├── app.yaml                    # App runtime configuration
├── .databricksignore           # Files to exclude from deployment
├── .gitignore                  # Git ignore patterns
├── .dockerignore               # Docker ignore patterns
│
├── app.py                      # Main Streamlit application
├── ucx_utils.py               # UCX troubleshooting utilities
├── model_serving_utils.py     # Model serving interface
│
└── ucx-codebase/              # Cached UCX repository
    ├── src/                   # UCX source code
    ├── docs/                  # UCX documentation
    ├── tests/                 # UCX tests (filtered)
    └── README.md              # UCX official README
```

## 🔧 Development

### **Local Development**

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

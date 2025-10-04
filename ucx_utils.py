"""
UCX Troubleshooting Utilities

This module provides utilities for accessing UCX documentation, logs, and 
troubleshooting information from a locally cached UCX codebase.
"""

import logging
import os
from typing import Dict, List
import glob

logger = logging.getLogger(__name__)


class UCXTroubleshooter:
    """UCX Troubleshooting Assistant"""
    
    def __init__(self, ucx_local_path: str = None):
        """
        Initialize UCX Troubleshooter
        
        Args:
            ucx_local_path: Path to local UCX codebase cache
        """
        if ucx_local_path is None:
            # Default to the cached UCX codebase in the same directory as this app
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.ucx_local_path = os.path.join(current_dir, "ucx-codebase")
        else:
            self.ucx_local_path = ucx_local_path
        
    def get_troubleshooting_docs(self) -> str:
        """Get UCX troubleshooting documentation from local cached UCX repository"""
        # Load troubleshooting docs from local UCX cache
        troubleshooting_paths = [
            os.path.join(self.ucx_local_path, "docs", "ucx", "docs", "reference", "troubleshooting.md"),
            os.path.join(self.ucx_local_path, "docs", "ucx", "docs", "reference", "troubleshooting.mdx"),
            os.path.join(self.ucx_local_path, "TROUBLESHOOTING.md"),
            os.path.join(self.ucx_local_path, "README.md")
        ]
        
        for path in troubleshooting_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"Successfully loaded UCX docs from {path}")
                    return content
            except Exception as e:
                logger.debug(f"Could not load {path}: {e}")
        
        # If no specific troubleshooting docs found, return README content
        readme_path = os.path.join(self.ucx_local_path, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # If no docs found, return default troubleshooting guide
        return self._get_default_troubleshooting_guide()
    
    def _check_ucx_codebase_exists(self) -> bool:
        """Check if local UCX codebase cache exists"""
        return os.path.exists(self.ucx_local_path) and os.path.exists(os.path.join(self.ucx_local_path, "src"))
    
    def get_ucx_source_files(self, pattern: str = "*.py") -> List[str]:
        """Get list of UCX source files matching pattern from local cache"""
        if not self._check_ucx_codebase_exists():
            return []
        
        src_path = os.path.join(self.ucx_local_path, "src")
        return glob.glob(os.path.join(src_path, "**", pattern), recursive=True)
    
    def analyze_ucx_errors_from_source(self) -> Dict[str, List[str]]:
        """Analyze UCX source code for common error patterns from local cache"""
        if not self._check_ucx_codebase_exists():
            return {"info": ["UCX codebase cache not available"]}
        
        error_patterns = {}
        python_files = self.get_ucx_source_files("*.py")
        
        # Common error patterns to look for
        patterns = {
            "authentication_errors": ["AuthenticationError", "auth", "token", "credentials"],
            "permission_errors": ["PermissionError", "privilege", "access denied", "forbidden"],
            "hive_metastore_errors": ["HiveMetastoreError", "HMS", "metastore", "hive"],
            "cluster_errors": ["ClusterError", "cluster", "compute", "driver"],
            "unity_catalog_errors": ["UnityCatalogError", "UC", "unity catalog"]
        }
        
        for error_type, keywords in patterns.items():
            error_patterns[error_type] = []
            for file_path in python_files[:10]:  # Limit to first 10 files for performance
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    for keyword in keywords:
                        if keyword.lower() in content.lower():
                            rel_path = os.path.relpath(file_path, self.ucx_local_path)
                            error_patterns[error_type].append(f"Found '{keyword}' in {rel_path}")
                            break  # Only add file once per error type
                except Exception as e:
                    logger.debug(f"Could not analyze {file_path}: {e}")
        
        return error_patterns

    def get_common_errors(self) -> Dict[str, str]:
        """Get common UCX errors and solutions"""
        return {
            "insufficient_privileges": {
                "error": "Insufficient privileges for UCX installation",
                "solution": "Ensure you have Databricks workspace "
                           "administrator privileges. UCX requires admin "
                           "access to deploy assets into the workspace.",
                "details": "The installation process needs to create "
                          "workflows, clusters, and other workspace resources."
            },
            "python_version": {
                "error": "Python version compatibility issues",
                "solution": "Upgrade to Python 3.10 or later. UCX requires "
                           "modern Python features for proper operation.",
                "details": "Check your cluster's Python version and ensure "
                          "it meets the minimum requirements."
            },
            "databricks_cli": {
                "error": "Databricks CLI issues",
                "solution": "Update Databricks CLI to v0.213 or higher. "
                           "Older versions may have compatibility issues.",
                "details": "Run 'databricks version' to check current version "
                          "and 'pip install --upgrade databricks-cli' to update."
            },
            "authentication": {
                "error": "Authentication failures during UCX operations",
                "solution": "Verify your authentication credentials. "
                           "Use DATABRICKS_HOST and DATABRICKS_TOKEN "
                           "environment variables or --profile flag.",
                "details": "Check token validity and workspace permissions."
            },
            "external_hms": {
                "error": "External Hive Metastore connectivity issues",
                "solution": "Verify network configuration and HMS connectivity. "
                           "Ensure firewall rules allow communication.",
                "details": "Check HMS endpoints, credentials, and network policies."
            },
            "cluster_config": {
                "error": "Cluster configuration or resource issues",
                "solution": "Check cluster policies and resource availability. "
                           "Ensure sufficient compute resources are allocated.",
                "details": "Review cluster logs and resource quotas."
            },
            "unity_catalog_not_enabled": {
                "error": "Unity Catalog not enabled in workspace",
                "solution": "Enable Unity Catalog in your Databricks workspace. "
                           "Contact your workspace admin if needed.",
                "details": "UCX requires Unity Catalog to be enabled for migration operations."
            }
        }
    
    def analyze_error_message(self, error_message: str) -> Dict[str, str]:
        """Analyze error message and provide targeted solutions"""
        error_message_lower = error_message.lower()
        
        if "permission" in error_message_lower or "privilege" in error_message_lower:
            return self.get_common_errors()["insufficient_privileges"]
        elif "python" in error_message_lower and "version" in error_message_lower:
            return self.get_common_errors()["python_version"]
        elif "databricks-cli" in error_message_lower or "cli" in error_message_lower:
            return self.get_common_errors()["databricks_cli"]
        elif "auth" in error_message_lower or "token" in error_message_lower:
            return self.get_common_errors()["authentication"]
        elif "hive" in error_message_lower or "metastore" in error_message_lower:
            return self.get_common_errors()["external_hms"]
        elif "cluster" in error_message_lower or "compute" in error_message_lower:
            return self.get_common_errors()["cluster_config"]
        elif "unity catalog" in error_message_lower or "uc" in error_message_lower:
            return self.get_common_errors()["unity_catalog_not_enabled"]
        else:
            return {
                "error": "Unknown error pattern",
                "solution": "Please check the UCX troubleshooting documentation or provide more details about the error.",
                "details": "For specific error analysis, please share the complete error message and context."
            }
    
    def get_installation_checklist(self) -> List[str]:
        """Get UCX installation checklist"""
        return [
            "✓ Verify you have Databricks workspace administrator privileges",
            "✓ Ensure Python 3.10+ is installed",
            "✓ Update Databricks CLI to v0.213 or higher",
            "✓ Verify Unity Catalog is enabled in your workspace",
            "✓ Check network connectivity to external resources if using external HMS",
            "✓ Ensure sufficient compute resources are available",
            "✓ Verify authentication credentials are valid",
            "✓ Check workspace storage permissions"
        ]

    def get_assessment_checklist(self) -> List[str]:
        """Get UCX assessment checklist"""
        return [
            "✓ UCX is successfully installed",
            "✓ Authentication is properly configured",
            "✓ Assessment cluster is running and accessible",
            "✓ Required permissions are granted for data scanning",
            "✓ External data sources are accessible (if applicable)",
            "✓ Sufficient workspace storage for assessment results",
            "✓ Network connectivity to all data sources"
        ]

    def _get_default_troubleshooting_guide(self) -> str:
        """Get default troubleshooting guide when UCX docs are not available"""
        return """
# UCX Troubleshooting Guide

## Common Installation Issues

### 1. Insufficient Privileges
**Error**: Permission denied during installation
**Solution**: Ensure you have Databricks workspace administrator privileges

### 2. Python Version Issues
**Error**: Python version compatibility errors
**Solution**: Upgrade to Python 3.10 or later

### 3. Databricks CLI Issues
**Error**: CLI command failures
**Solution**: Update to Databricks CLI v0.213 or higher

## Common Assessment Issues

### 1. Authentication Failures
**Error**: Unable to authenticate during assessment
**Solution**: Verify DATABRICKS_ environment variables or use --profile flag

### 2. Cluster Configuration Issues
**Error**: Assessment job fails to start
**Solution**: Check cluster policies and resource availability

### 3. External HMS Issues
**Error**: Cannot connect to external Hive Metastore
**Solution**: Verify network configuration and HMS connectivity

## Getting Help

1. Check UCX logs in /Workspace/Applications/ucx/logs/
2. Review the complete error message and stack trace
3. Verify your environment meets all prerequisites
4. Consult the UCX documentation for detailed guidance
"""

def create_ucx_context(user_message: str) -> str:
    """Create UCX-specific context for the chatbot using cached UCX codebase"""
    try:
        troubleshooter = UCXTroubleshooter()
        
        # Check if we have the cached codebase
        if not troubleshooter._check_ucx_codebase_exists():
            return f"""
⚠️ **UCX Codebase Cache Missing**

This UCX troubleshooting assistant includes a cached version of the UCX codebase for enhanced analysis, but the cache is not available.

**Current Capabilities:**
- ✅ Built-in UCX troubleshooting knowledge
- ✅ Common error patterns and solutions  
- ✅ Installation and assessment checklists
- ❌ Live source code analysis (cache missing)

**Available Help:**
{chr(10).join(troubleshooter.get_installation_checklist())}

I can still help with your UCX questions using built-in expertise. What issue are you experiencing?
"""
        
        # Get actual UCX documentation
        ucx_docs = troubleshooter.get_troubleshooting_docs()
        
        # Get errors from actual source code analysis
        source_errors = troubleshooter.analyze_ucx_errors_from_source()
        
        # Analyze if this is an error message
        if any(keyword in user_message.lower() for keyword in ['error', 'fail', 'issue', 'problem', 'trouble']):
            error_analysis = troubleshooter.analyze_error_message(user_message)
            
            context = f"""
You are a UCX (Unity Catalog Migration Assistant) troubleshooting expert with access to the cached UCX codebase from https://github.com/databrickslabs/ucx.

**User's Issue Analysis:**
- Error Type: {error_analysis['error']}
- Solution: {error_analysis['solution']}
- Details: {error_analysis['details']}

**UCX Official Documentation:**
{ucx_docs[:2000]}...

**Errors Found in UCX Source Code:**
{str(source_errors)[:1000]}...

**Installation Checklist:**
{chr(10).join(troubleshooter.get_installation_checklist())}

Please provide specific, actionable advice based on the actual UCX codebase and documentation.
"""
        else:
            # General UCX assistance
            context = f"""
You are a UCX (Unity Catalog Migration Assistant) expert assistant with access to the cached UCX codebase from https://github.com/databrickslabs/ucx.

**UCX Official Documentation:**
{ucx_docs[:2000]}...

**Installation Checklist:**
{chr(10).join(troubleshooter.get_installation_checklist())}

**Assessment Checklist:**
{chr(10).join(troubleshooter.get_assessment_checklist())}

**Source Code Analysis:**
Found {len(troubleshooter.get_ucx_source_files())} UCX source files for deep analysis.

Please help the user with their UCX-related questions using the cached UCX codebase and documentation.
"""
        
        return context
        
    except Exception as e:
        # Fallback to built-in knowledge
        troubleshooter = UCXTroubleshooter()
        return f"""
⚠️ **UCX Assistant - Built-in Mode**

Using built-in UCX troubleshooting knowledge (enhanced codebase analysis temporarily unavailable).

**Error encountered:** {str(e)[:200]}...

**Available Help:**
**Installation Checklist:**
{chr(10).join(troubleshooter.get_installation_checklist())}

**Assessment Checklist:**
{chr(10).join(troubleshooter.get_assessment_checklist())}

**Common Issues:** Use the sidebar buttons for quick access to common errors and solutions.

I can still help with your UCX questions using comprehensive built-in expertise. What issue are you experiencing?
"""
"""
UCX Troubleshooting Utilities
"""

import logging
import os
from typing import Dict, List
import glob

logger = logging.getLogger(__name__)


class UCXTroubleshooter:
    """UCX Troubleshooting Assistant"""
        
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
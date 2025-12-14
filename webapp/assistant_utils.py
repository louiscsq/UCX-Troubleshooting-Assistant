"""
Troubleshooting Assistant Utilities
"""

import yaml
from typing import Dict, List

# Load configuration
import os
config_file = os.getenv('CONFIG_FILE', 'configs/ucx.config.yaml')
config_path = os.path.join(os.path.dirname(__file__), config_file)
with open(config_path, 'r') as f:
    CONFIG = yaml.safe_load(f)


class AssistantTroubleshooter:
    """Troubleshooting Assistant"""
        
    def get_installation_checklist(self) -> List[str]:
        """Get installation checklist from config"""
        return CONFIG.get('installation_checklist', [])

    def get_assessment_checklist(self) -> List[str]:
        """Get assessment checklist from config"""
        return CONFIG.get('assessment_checklist', [])

    def analyze_error_message(self, error_message: str) -> Dict[str, str]:
        """Analyze error message and provide targeted solutions"""
        error_message_lower = error_message.lower()
        common_errors = self.get_common_errors()
        
        # Default response if no matching error is found
        default_error = {
            "error": "Unknown error pattern",
            "solution": f"Please check the {CONFIG.get('project_name', 'troubleshooting')} documentation or provide more details about the error.",
            "details": "For specific error analysis, please share the complete error message and context."
        }
        
        # Check for error patterns and return if the error key exists in config
        if "permission" in error_message_lower or "privilege" in error_message_lower:
            return common_errors.get("insufficient_privileges", default_error)
        elif "python" in error_message_lower and "version" in error_message_lower:
            return common_errors.get("python_version", default_error)
        elif "databricks-cli" in error_message_lower or "cli" in error_message_lower:
            return common_errors.get("databricks_cli", default_error)
        elif "auth" in error_message_lower or "token" in error_message_lower:
            return common_errors.get("authentication", default_error)
        elif "hive" in error_message_lower or "metastore" in error_message_lower:
            return common_errors.get("external_hms", default_error)
        elif "cluster" in error_message_lower or "compute" in error_message_lower:
            return common_errors.get("cluster_config", default_error)
        elif "unity catalog" in error_message_lower or "uc" in error_message_lower:
            return common_errors.get("unity_catalog_not_enabled", default_error)
        elif "ssl" in error_message_lower or "certificate" in error_message_lower:
            # Check for SSL-related errors (common in both configs)
            if "certificate_verify_failed" in error_message_lower or "unable to get local issuer" in error_message_lower:
                return common_errors.get("ssl_certificate_not_found", default_error)
            elif "basic constraints" in error_message_lower or "not marked critical" in error_message_lower:
                return common_errors.get("ssl_certificate_noncritical_constraint", default_error)
            return default_error
        else:
            return default_error
    def get_common_errors(self) -> Dict[str, Dict[str, str]]:
        """Get common errors and solutions from config"""
        return CONFIG.get('errors', {})


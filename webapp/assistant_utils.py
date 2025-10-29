"""
Troubleshooting Assistant Utilities
"""

import logging
import yaml
from typing import Dict, List

logger = logging.getLogger(__name__)

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
                "solution": f"Please check the {CONFIG.get('project_name', 'troubleshooting')} documentation or provide more details about the error.",
                "details": "For specific error analysis, please share the complete error message and context."
            }
    def get_common_errors(self) -> Dict[str, Dict[str, str]]:
        """Get common errors and solutions from config"""
        return CONFIG.get('errors', {})


"""
UCX Troubleshooting Assistant - Configuration Helper

This utility helps manage audit table configuration across different environments.
"""

import os
from typing import Dict, Any

class AuditConfig:
    """Configuration helper for audit system"""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get current audit configuration from environment"""
        return {
            'catalog_name': os.getenv('AUDIT_CATALOG', 'main'),
            'schema_name': os.getenv('AUDIT_SCHEMA', 'ucx_audit'),
            'table_name': os.getenv('AUDIT_TABLE', 'chat_interactions'),
            'full_table_name': f"{os.getenv('AUDIT_CATALOG', 'main')}.{os.getenv('AUDIT_SCHEMA', 'ucx_audit')}.{os.getenv('AUDIT_TABLE', 'chat_interactions')}"
        }
    
    @staticmethod
    def validate_config() -> Dict[str, Any]:
        """Validate audit configuration and return status"""
        config = AuditConfig.get_config()
        
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        def is_valid_identifier(name: str) -> bool:
            """Check if name follows Unity Catalog naming conventions"""
            if not name or len(name) == 0:
                return False
            
            # Unity Catalog allows: letters, numbers, underscores, hyphens
            # Must start with letter or underscore
            # Cannot be empty after removing valid characters
            import re
            pattern = r'^[a-zA-Z_][a-zA-Z0-9_-]*$'
            return bool(re.match(pattern, name)) and len(name) <= 255
        
        # Validate catalog name
        if not is_valid_identifier(config['catalog_name']):
            validation['valid'] = False
            validation['errors'].append(f"Invalid catalog name '{config['catalog_name']}'. Must start with letter/underscore and contain only letters, numbers, hyphens, underscores.")
        
        # Validate schema name  
        if not is_valid_identifier(config['schema_name']):
            validation['valid'] = False
            validation['errors'].append(f"Invalid schema name '{config['schema_name']}'. Must start with letter/underscore and contain only letters, numbers, hyphens, underscores.")
        
        # Validate table name
        if not is_valid_identifier(config['table_name']):
            validation['valid'] = False
            validation['errors'].append(f"Invalid table name '{config['table_name']}'. Must start with letter/underscore and contain only letters, numbers, hyphens, underscores.")
        
        # Add warnings for common issues
        if config['catalog_name'] == 'main' and config['schema_name'] == 'ucx_audit':
            validation['warnings'].append("Using default catalog and schema. Consider using environment-specific names for production.")
        
        validation['config'] = config
        return validation
    
    @staticmethod
    def display_config_info():
        """Display current configuration info for debugging"""
        import streamlit as st
        
        config = AuditConfig.get_config()
        validation = AuditConfig.validate_config()
        
        with st.expander("🔧 Audit Configuration", expanded=False):
            if validation['valid']:
                st.success("✅ Configuration is valid")
            else:
                st.error("❌ Configuration has errors")
                for error in validation['errors']:
                    st.error(f"• {error}")
            
            if validation['warnings']:
                for warning in validation['warnings']:
                    st.warning(f"⚠️ {warning}")
            
            st.json(config)
            
            st.write("**Environment Variables:**")
            st.code(f"""
export AUDIT_CATALOG="{config['catalog_name']}"
export AUDIT_SCHEMA="{config['schema_name']}"  
export AUDIT_TABLE="{config['table_name']}"
            """)

# Configuration presets for different environments
ENVIRONMENT_PRESETS = {
    'development': {
        'catalog_name': 'main',
        'schema_name': 'ucx_audit_dev',
        'table_name': 'chat_interactions'
    },
    'staging': {
        'catalog_name': 'main',
        'schema_name': 'ucx_audit_staging',
        'table_name': 'chat_interactions'
    },
    'production': {
        'catalog_name': 'main',
        'schema_name': 'ucx_audit_prod',
        'table_name': 'chat_interactions'
    },
    'shared': {
        'catalog_name': 'shared',
        'schema_name': 'ucx_audit',
        'table_name': 'chat_interactions'
    }
}

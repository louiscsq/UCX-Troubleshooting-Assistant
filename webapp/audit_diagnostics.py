"""
UCX Troubleshooting Assistant - Audit System Diagnostics

This utility helps diagnose and troubleshoot audit system issues.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
import streamlit as st

logger = logging.getLogger(__name__)

class AuditDiagnostics:
    """Diagnostic utilities for the audit system"""
    
    @staticmethod
    def diagnose_audit_system() -> Dict[str, Any]:
        """
        Comprehensive diagnosis of the audit system
        
        Returns:
            Dictionary with diagnosis results and recommendations
        """
        diagnosis = {
            'environment': {},
            'configuration': {},
            'storage': {},
            'recommendations': [],
            'status': 'unknown'
        }
        
        # Check environment
        try:
            from pyspark.sql import SparkSession
            spark_available = True
            try:
                spark = SparkSession.getActiveSession()
                spark_active = spark is not None
            except:
                spark_active = False
        except ImportError:
            spark_available = False
            spark_active = False
        
        try:
            from databricks.sdk import WorkspaceClient
            databricks_sdk_available = True
        except ImportError:
            databricks_sdk_available = True
        
        diagnosis['environment'] = {
            'spark_available': spark_available,
            'spark_active': spark_active,
            'databricks_sdk_available': databricks_sdk_available,
            'environment_type': 'databricks' if spark_active else 'local'
        }
        
        # Check configuration
        from config_helper import AuditConfig
        config_validation = AuditConfig.validate_config()
        diagnosis['configuration'] = config_validation
        
        # Check storage
        if spark_active:
            # Delta Lake mode
            diagnosis['storage'] = {
                'mode': 'delta_lake',
                'table_name': config_validation['config']['full_table_name'],
                'status': 'available'
            }
            diagnosis['status'] = 'delta_mode'
        else:
            # JSON fallback mode
            audit_dir = Path("audit_logs")
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            audit_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
            
            diagnosis['storage'] = {
                'mode': 'json_fallback',
                'audit_dir': str(audit_dir),
                'audit_file': str(audit_file),
                'dir_exists': audit_dir.exists(),
                'file_exists': audit_file.exists(),
                'file_size': audit_file.stat().st_size if audit_file.exists() else 0
            }
            diagnosis['status'] = 'json_mode'
        
        # Generate recommendations
        recommendations = []
        
        if not spark_active:
            recommendations.append("Deploy to Databricks environment to enable Delta Lake audit features")
        
        if diagnosis['storage']['mode'] == 'json_fallback':
            if not diagnosis['storage']['dir_exists']:
                recommendations.append("Create audit_logs directory for JSON file storage")
            if not diagnosis['storage']['file_exists']:
                recommendations.append("Audit file will be created when first interaction occurs")
        
        if not config_validation['valid']:
            recommendations.extend([f"Fix configuration: {error}" for error in config_validation['errors']])
        
        diagnosis['recommendations'] = recommendations
        
        return diagnosis
    
    @staticmethod
    def display_diagnostics():
        """Display audit system diagnostics in Streamlit"""
        st.subheader("🔧 Audit System Diagnostics")
        
        diagnosis = AuditDiagnostics.diagnose_audit_system()
        
        # Status overview
        if diagnosis['status'] == 'delta_mode':
            st.success("✅ **Status**: Delta Lake Mode (Production Ready)")
        elif diagnosis['status'] == 'json_mode':
            st.warning("⚠️ **Status**: JSON Fallback Mode (Development/Local)")
        else:
            st.error("❌ **Status**: Unknown - System may have issues")
        
        # Environment details
        with st.expander("🌐 Environment Details"):
            env = diagnosis['environment']
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Environment Type", env['environment_type'].title())
                st.metric("Spark Available", "✅" if env['spark_available'] else "❌")
            
            with col2:
                st.metric("Spark Active", "✅" if env['spark_active'] else "❌") 
                st.metric("Databricks SDK", "✅" if env['databricks_sdk_available'] else "❌")
        
        # Storage details
        with st.expander("💾 Storage Configuration"):
            storage = diagnosis['storage']
            
            if storage['mode'] == 'delta_lake':
                st.success(f"**Mode**: Delta Lake")
                st.code(f"Table: {storage['table_name']}")
            else:
                st.warning(f"**Mode**: JSON Fallback")
                st.code(f"""
Directory: {storage['audit_dir']}
File: {storage['audit_file']}
Directory Exists: {storage['dir_exists']}
File Exists: {storage['file_exists']}
File Size: {storage['file_size']} bytes
                """)
        
        # Configuration validation
        with st.expander("⚙️ Configuration Validation"):
            config = diagnosis['configuration']
            if config['valid']:
                st.success("✅ Configuration is valid")
            else:
                st.error("❌ Configuration has issues")
                for error in config['errors']:
                    st.error(f"• {error}")
            
            if config['warnings']:
                for warning in config['warnings']:
                    st.warning(f"⚠️ {warning}")
        
        # Recommendations
        if diagnosis['recommendations']:
            st.subheader("💡 Recommendations")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                st.info(f"{i}. {rec}")
        
        # Quick fixes
        st.subheader("🚀 Quick Fixes")
        
        if diagnosis['storage']['mode'] == 'json_fallback':
            if st.button("Initialize Audit System"):
                try:
                    # Create audit directory and empty file
                    audit_dir = Path("audit_logs")
                    audit_dir.mkdir(exist_ok=True)
                    
                    from datetime import datetime
                    today = datetime.now().strftime("%Y-%m-%d")
                    audit_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
                    
                    # Create empty file
                    with open(audit_file, 'w', encoding='utf-8') as f:
                        pass
                    
                    st.success(f"✅ Created audit file: {audit_file}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Failed to initialize: {e}")
        
        return diagnosis

def fix_audit_initialization():
    """Fix common audit initialization issues"""
    try:
        # Ensure audit directory exists
        audit_dir = Path("audit_logs")
        audit_dir.mkdir(exist_ok=True)
        
        # Create today's audit file if it doesn't exist
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        audit_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
        
        if not audit_file.exists():
            with open(audit_file, 'w', encoding='utf-8') as f:
                pass  # Create empty file
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix audit initialization: {e}")
        return False

"""
Spark Diagnostics for Databricks Apps
"""

import logging
import os
import streamlit as st

logger = logging.getLogger(__name__)

def diagnose_spark_environment():
    """Comprehensive Spark environment diagnostics"""
    
    st.subheader("🔍 Spark Environment Diagnostics")
    
    diagnostics = {
        'environment_vars': {},
        'imports': {},
        'spark_availability': {},
        'errors': []
    }
    
    # Check environment variables
    spark_related_vars = [
        'SPARK_HOME', 'PYSPARK_PYTHON', 'DATABRICKS_RUNTIME_VERSION',
        'SPARK_CONF_DIR', 'JAVA_HOME', 'PYTHONPATH'
    ]
    
    for var in spark_related_vars:
        diagnostics['environment_vars'][var] = os.getenv(var, 'Not Set')
    
    # Check imports
    try:
        from pyspark.sql import SparkSession
        diagnostics['imports']['pyspark'] = '✅ Available'
        
        # Try to get existing session
        try:
            current_session = SparkSession.getActiveSession()
            if current_session:
                diagnostics['spark_availability']['existing_session'] = f"✅ Found: {current_session.sparkContext.appName}"
                diagnostics['spark_availability']['spark_version'] = current_session.version
                diagnostics['spark_availability']['master'] = current_session.sparkContext.master
            else:
                diagnostics['spark_availability']['existing_session'] = "❌ No active session"
        except Exception as e:
            diagnostics['errors'].append(f"Error checking existing session: {e}")
        
        # Try to create new session
        try:
            test_session = SparkSession.builder.appName("DiagnosticTest").getOrCreate()
            diagnostics['spark_availability']['new_session'] = f"✅ Created: {test_session.sparkContext.appName}"
            diagnostics['spark_availability']['cluster_mode'] = test_session.sparkContext.master
            
            # Test basic SQL
            try:
                df = test_session.sql("SELECT 1 as test")
                result = df.collect()
                diagnostics['spark_availability']['sql_test'] = f"✅ SQL works: {result}"
            except Exception as e:
                diagnostics['errors'].append(f"SQL test failed: {e}")
                
        except Exception as e:
            diagnostics['errors'].append(f"Failed to create Spark session: {e}")
            diagnostics['spark_availability']['new_session'] = f"❌ Failed: {e}"
            
    except ImportError as e:
        diagnostics['imports']['pyspark'] = f'❌ Import failed: {e}'
    
    # Check Delta
    try:
        from delta.tables import DeltaTable
        diagnostics['imports']['delta'] = '✅ Available'
    except ImportError as e:
        diagnostics['imports']['delta'] = f'❌ Import failed: {e}'
    
    # Check Databricks SDK
    try:
        from databricks.sdk import WorkspaceClient
        diagnostics['imports']['databricks_sdk'] = '✅ Available'
        
        try:
            ws = WorkspaceClient()
            diagnostics['spark_availability']['workspace_client'] = '✅ Connected'
        except Exception as e:
            diagnostics['errors'].append(f"WorkspaceClient failed: {e}")
            
    except ImportError as e:
        diagnostics['imports']['databricks_sdk'] = f'❌ Import failed: {e}'
    
    # Display results
    with st.expander("📊 Environment Variables", expanded=False):
        for var, value in diagnostics['environment_vars'].items():
            if value != 'Not Set':
                st.success(f"**{var}**: `{value}`")
            else:
                st.warning(f"**{var}**: Not Set")
    
    with st.expander("📦 Import Status", expanded=True):
        for module, status in diagnostics['imports'].items():
            if '✅' in status:
                st.success(f"**{module}**: {status}")
            else:
                st.error(f"**{module}**: {status}")
    
    with st.expander("⚡ Spark Availability", expanded=True):
        for check, result in diagnostics['spark_availability'].items():
            if '✅' in result:
                st.success(f"**{check}**: {result}")
            else:
                st.error(f"**{check}**: {result}")
    
    if diagnostics['errors']:
        with st.expander("❌ Errors", expanded=True):
            for error in diagnostics['errors']:
                st.error(f"• {error}")
    
    return diagnostics

def show_compute_recommendations():
    """Show recommendations for enabling Spark in Databricks Apps"""
    
    st.subheader("💡 Compute Configuration Recommendations")
    
    st.info("""
    **Databricks Apps Spark Requirements:**
    
    Databricks Apps need explicit compute configuration to access Spark. Try these configurations in your `app.yaml`:
    """)
    
    tab1, tab2, tab3 = st.tabs(["Shared Compute", "Serverless Compute", "Custom Cluster"])
    
    with tab1:
        st.code("""
# app.yaml - Shared Compute Configuration
compute:
  spec:
    kind: "shared_compute"
        """, language="yaml")
        st.info("Uses shared Databricks compute resources")
    
    with tab2:
        st.code("""
# app.yaml - Serverless Compute Configuration  
compute:
  spec:
    kind: "serverless"
        """, language="yaml")
        st.info("Uses serverless compute (if available in your workspace)")
    
    with tab3:
        st.code("""
# app.yaml - Custom Cluster Configuration
compute:
  spec:
    kind: "compute_specification"
    compute_specification:
      kind: "fixed_node_type_compute_specification"
      node_type_id: "i3.xlarge"
      num_workers: 1
        """, language="yaml")
        st.info("Creates a dedicated cluster for the app")

if __name__ == "__main__":
    st.title("🔍 Spark Diagnostics")
    diagnose_spark_environment()
    show_compute_recommendations()

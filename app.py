import logging
import os
import time
import uuid
import streamlit as st
from model_serving_utils import query_endpoint, is_endpoint_supported
from ucx_utils import create_ucx_context, UCXTroubleshooter
from audit_utils import get_auditor, PrivacyManager
from simple_audit_utils import get_simple_auditor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure environment variable is set correctly
SERVING_ENDPOINT = os.getenv('SERVING_ENDPOINT')
assert SERVING_ENDPOINT, \
    ("Unable to determine serving endpoint to use for chatbot app. If developing locally, "
     "set the SERVING_ENDPOINT environment variable to the name of your serving endpoint. If "
     "deploying to a Databricks app, include a serving endpoint resource named "
     "'serving_endpoint' with CAN_QUERY permissions, as described in "
     "https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app#deploy-the-databricks-app")

# Check if the endpoint is supported
endpoint_supported = is_endpoint_supported(SERVING_ENDPOINT)

def get_user_info():
    headers = st.context.headers
    return dict(
        user_name=headers.get("X-Forwarded-Preferred-Username"),
        user_email=headers.get("X-Forwarded-Email"),
        user_id=headers.get("X-Forwarded-User"),
    )

user_info = get_user_info()

# Initialize audit logging with true Delta Lake via SQL
logger.info("🚀 Starting audit system initialization...")
try:
    from sql_audit_utils import get_sql_auditor
    logger.info("📊 Attempting SQL-based Delta Lake auditor...")
    auditor = get_sql_auditor()
    
    # Check if it's really working or fell back to JSON
    if hasattr(auditor, '_use_fallback') and auditor._use_fallback:
        logger.warning("⚠️ SQL auditor fell back to JSON mode")
        audit_mode = "fallback"
    else:
        audit_mode = "sql_warehouse"
        logger.info("✅ SQL-based Delta Lake auditor initialized successfully!")
        
except Exception as e:
    import traceback
    logger.error(f"❌ SQL Delta auditor initialization failed: {e}")
    logger.error(f"Full traceback: {traceback.format_exc()}")
    logger.warning("⚠️ Falling back to simulation mode...")
    try:
        from simple_audit_utils import get_simple_auditor
        auditor = get_simple_auditor()
        audit_mode = "delta_simulation"
        logger.info("✅ Using Delta simulation as fallback")
    except Exception as e2:
        logger.error(f"❌ All Delta auditors failed: {e2}")
        logger.warning("⚠️ Using JSON fallback mode")
        auditor = get_auditor()
        audit_mode = "fallback"

logger.info(f"🎯 Final audit mode: {audit_mode}")
logger.info(f"🔧 Auditor type: {type(auditor).__name__}")

# Generate session ID for audit tracking
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Display audit configuration in debug mode (optional)
if os.getenv('AUDIT_DEBUG', 'false').lower() == 'true':
    audit_config = {
        'catalog': os.getenv('AUDIT_CATALOG', 'main'),
        'schema': os.getenv('AUDIT_SCHEMA', 'ucx_audit'),
        'table': os.getenv('AUDIT_TABLE', 'chat_interactions')
    }
    logger.info(f"Audit configuration: {audit_config}")

# Streamlit app
if "visibility" not in st.session_state:
    st.session_state.visibility = "visible"
    st.session_state.disabled = False

st.title("🔧 UCX Troubleshooting Assistant")

# Check for admin dashboard access via URL parameters
admin_access = False
diagnostics_access = False

# Simplified query parameter detection + always show test buttons
admin_access = False
diagnostics_access = False

# Check session state for manual triggers
if "test_admin" in st.session_state and st.session_state.test_admin:
    admin_access = True
if "test_debug" in st.session_state and st.session_state.test_debug:
    diagnostics_access = True

# Check for admin access via URL parameters  
try:
    # Check for admin parameter
    admin_param = st.query_params.get('admin', '')
    debug_param = st.query_params.get('debug', '')
    
    if admin_param == 'dashboard':
        st.session_state.test_admin = True
        st.session_state.test_debug = False
        admin_access = True
    elif debug_param == 'spark':
        st.session_state.test_debug = True
        st.session_state.test_admin = False  
        diagnostics_access = True
    # If no URL params, preserve existing session state
    elif "test_admin" in st.session_state and st.session_state.test_admin:
        admin_access = True
    elif "test_debug" in st.session_state and st.session_state.test_debug:
        diagnostics_access = True
        
except Exception as e:
    # Fallback to session state
    if "test_admin" in st.session_state and st.session_state.test_admin:
        admin_access = True
    elif "test_debug" in st.session_state and st.session_state.test_debug:
        diagnostics_access = True

# Show audit dashboard if accessed with special URL parameter
if admin_access:
    st.info("🔒 **Admin Access Detected** - Showing Audit Dashboard")
    
    # Pass the same auditor instance to the dashboard
    from audit_dashboard import AuditDashboard
    dashboard = AuditDashboard()
    dashboard.auditor = auditor  # Use the same auditor as main app
    dashboard.audit_mode = audit_mode
    dashboard.render()

    # Log admin access
    auditor.log_interaction(
        session_id=st.session_state.session_id,
        user_info=user_info,
        user_question="Admin Dashboard Access",
        assistant_response="Accessed audit dashboard via admin URL",
        response_time_ms=0,
        endpoint_used="N/A",
        interaction_type="admin_access",
        ucx_context_used=False
    )

    # Stop here - don't show the normal app interface
    st.stop()

# Show Spark diagnostics if accessed with special URL parameter
if diagnostics_access:
    st.info("🔍 **Debug Mode** - SQL Warehouse & Environment Diagnostics")
    
    # Check current auditor mode
    st.subheader("📊 Current Audit Mode")
    if audit_mode == "sql_warehouse":
        st.success("✅ Using SQL Warehouse Delta Lake mode")
        st.info("🏛️ Real Delta tables with full ACID capabilities!")
        st.code(f"Active auditor: {type(auditor).__name__}")
        st.code(f"Table: {auditor.full_table_name}")
        st.code(f"Warehouse: {auditor.warehouse.id if hasattr(auditor, 'warehouse') else 'Not set'}")
    elif audit_mode == "delta_simulation":
        st.success("✅ Using Delta Table simulation mode")
        st.info("🎯 JSON backend with Delta Table presentation - best UX!")
        st.code(f"Active auditor: {type(auditor).__name__}")
        
        # Show connection status
        if hasattr(auditor, 'databricks_connected') and auditor.databricks_connected:
            st.success("✅ Connected to Databricks workspace")
        else:
            st.warning("⚠️ Not connected to workspace (expected in local testing)")
    else:
        st.warning("⚠️ Using JSON fallback audit mode") 
        st.code(f"Active auditor: {type(auditor).__name__}")
    
    # Add SQL warehouse diagnostics
    st.subheader("🏭 SQL Warehouse Check")
    try:
        from databricks.sdk import WorkspaceClient
        ws = WorkspaceClient()
        warehouses = list(ws.warehouses.list())
        if warehouses:
            st.success(f"✅ Found {len(warehouses)} SQL warehouse(s)")
            for wh in warehouses[:3]:  # Show first 3
                st.info(f"📊 {wh.name} (ID: {wh.id}) - State: {wh.state}")
        else:
            st.error("❌ No SQL warehouses found in workspace")
    except Exception as e:
        st.error(f"❌ Failed to list SQL warehouses: {e}")
    
    # Test SQL auditor initialization
    st.subheader("🧪 SQL Auditor Test")
    try:
        from sql_audit_utils import get_sql_auditor
        test_auditor = get_sql_auditor()
        st.success("✅ SQL auditor can be initialized")
        st.info(f"Target table: {test_auditor.full_table_name}")
        st.info(f"Using fallback mode: {test_auditor._use_fallback}")
        
        # Test table creation - Always show this button
        st.markdown("### 🔨 Manual Table Creation")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔨 Force Create Delta Table", key="force_create"):
                with st.spinner("Creating Delta table..."):
                    try:
                        st.info("🔨 Starting table creation process...")
                        test_auditor._initialize_audit_table()
                        st.success("✅ Delta table creation completed!")
                        st.info("✨ Check the catalog/schema in Databricks UI")
                        st.balloons()
                    except Exception as table_error:
                        st.error(f"❌ Table creation failed: {table_error}")
                        import traceback
                        st.code(traceback.format_exc())
        
        with col2:
            if st.button("🧪 Test SQL Execution", key="test_sql"):
                with st.spinner("Testing SQL execution..."):
                    try:
                        # Test basic SQL execution
                        result = test_auditor._execute_sql("SELECT 1 as test_value")
                        st.success("✅ SQL execution works!")
                        st.json({"result": str(result)})
                    except Exception as sql_error:
                        st.error(f"❌ SQL execution failed: {sql_error}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # Step-by-step diagnostics
        st.markdown("### 🔍 Step-by-Step Diagnostics")
        
        if st.button("🔍 Test Catalog Creation", key="test_catalog"):
            with st.spinner("Testing catalog creation..."):
                try:
                    catalog_sql = f"CREATE CATALOG IF NOT EXISTS {test_auditor.catalog_name}"
                    st.info(f"Executing: {catalog_sql}")
                    result = test_auditor._execute_sql(catalog_sql)
                    st.success("✅ Catalog creation command succeeded!")
                    st.json({"status": str(result.status), "statement_id": result.statement_id})
                    
                    # Test if catalog exists
                    check_sql = f"SHOW CATALOGS LIKE '{test_auditor.catalog_name}'"
                    st.info(f"Checking: {check_sql}")
                    check_result = test_auditor._execute_sql(check_sql)
                    if check_result.result and check_result.result.data_array:
                        st.success(f"✅ Catalog '{test_auditor.catalog_name}' exists!")
                        st.json({"catalogs_found": check_result.result.data_array})
                    else:
                        st.error(f"❌ Catalog '{test_auditor.catalog_name}' not found after creation!")
                        
                except Exception as e:
                    st.error(f"❌ Catalog test failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        if st.button("🔍 Test Schema Creation", key="test_schema"):
            with st.spinner("Testing schema creation..."):
                try:
                    schema_sql = f"CREATE SCHEMA IF NOT EXISTS {test_auditor.catalog_name}.{test_auditor.schema_name}"
                    st.info(f"Executing: {schema_sql}")
                    result = test_auditor._execute_sql(schema_sql)
                    st.success("✅ Schema creation command succeeded!")
                    st.json({"status": str(result.status), "statement_id": result.statement_id})
                    
                    # Test if schema exists
                    check_sql = f"SHOW SCHEMAS IN {test_auditor.catalog_name} LIKE '{test_auditor.schema_name}'"
                    st.info(f"Checking: {check_sql}")
                    check_result = test_auditor._execute_sql(check_sql)
                    if check_result.result and check_result.result.data_array:
                        st.success(f"✅ Schema '{test_auditor.schema_name}' exists!")
                        st.json({"schemas_found": check_result.result.data_array})
                    else:
                        st.error(f"❌ Schema '{test_auditor.schema_name}' not found after creation!")
                        
                except Exception as e:
                    st.error(f"❌ Schema test failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        if st.button("🔍 Check Available Catalogs", key="test_catalogs"):
            with st.spinner("Checking available catalogs..."):
                try:
                    # Check current user
                    user_sql = "SELECT current_user() as current_user"
                    st.info(f"Executing: {user_sql}")
                    user_result = test_auditor._execute_sql(user_sql)
                    if user_result.result and user_result.result.data_array:
                        current_user = user_result.result.data_array[0][0]
                        st.success(f"✅ Current user: {current_user}")
                    
                    # Show all catalogs user can see
                    catalogs_sql = "SHOW CATALOGS"
                    st.info(f"Executing: {catalogs_sql}")
                    catalogs_result = test_auditor._execute_sql(catalogs_sql)
                    if catalogs_result.result and catalogs_result.result.data_array:
                        st.success("✅ Available catalogs:")
                        for catalog_row in catalogs_result.result.data_array:
                            catalog_name = catalog_row[0]
                            st.info(f"📊 {catalog_name}")
                            
                            # Test if user can create schema in this catalog
                            try:
                                test_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.test_permissions_schema"
                                test_result = test_auditor._execute_sql(test_schema_sql)
                                st.success(f"✅ Can create schemas in '{catalog_name}'")
                                
                                # Clean up test schema
                                cleanup_sql = f"DROP SCHEMA IF EXISTS {catalog_name}.test_permissions_schema"
                                test_auditor._execute_sql(cleanup_sql)
                                st.info(f"🧹 Cleaned up test schema in '{catalog_name}'")
                                
                            except Exception as schema_error:
                                st.warning(f"⚠️ Cannot create schemas in '{catalog_name}': {schema_error}")
                    else:
                        st.error("❌ No catalogs found")
                        
                except Exception as e:
                    st.error(f"❌ Catalog check failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        if st.button("🔄 Switch to 'main' Catalog", key="switch_main"):
            with st.spinner("Testing 'main' catalog..."):
                try:
                    # Test creating schema in main catalog
                    test_schema_sql = "CREATE SCHEMA IF NOT EXISTS main.ucx_assistant_dev"
                    st.info(f"Executing: {test_schema_sql}")
                    result = test_auditor._execute_sql(test_schema_sql)
                    st.success("✅ Can create schema in 'main' catalog!")
                    st.json({"status": str(result.status), "statement_id": result.statement_id})
                    
                    # Update the configuration to use 'main'
                    st.info("💡 **Recommendation**: Update your configuration to use 'main' catalog instead of 'louis'")
                    st.code("""
# In app.yaml, change:
- name: "AUDIT_CATALOG"
  value: "main"  # Changed from "louis"
""")
                    
                except Exception as e:
                    st.error(f"❌ Cannot use 'main' catalog: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        if st.button("🏗️ Test Table Creation Only", key="test_table"):
            with st.spinner("Testing table creation..."):
                try:
                    # Test creating the specific audit table
                    table_sql = f"""
                    CREATE TABLE IF NOT EXISTS {test_auditor.full_table_name} (
                        timestamp TIMESTAMP,
                        session_id STRING,
                        user_name STRING,
                        user_email STRING,
                        user_id STRING,
                        user_question STRING,
                        assistant_response STRING,
                        ucx_context_used BOOLEAN,
                        error_type_detected STRING,
                        response_time_ms BIGINT,
                        endpoint_used STRING,
                        interaction_type STRING
                    ) USING DELTA
                    TBLPROPERTIES (
                        'description' = 'UCX Troubleshooting Assistant Audit Log',
                        'created_by' = 'UCX-Troubleshooting-Assistant',
                        'data_classification' = 'internal_audit'
                    )
                    """
                    
                    st.info(f"Creating table: {test_auditor.full_table_name}")
                    st.code(table_sql)
                    result = test_auditor._execute_sql(table_sql)
                    st.success("✅ Table creation command succeeded!")
                    st.json({"status": str(result.status), "statement_id": result.statement_id})
                    
                    # Test if table exists
                    check_sql = f"SHOW TABLES IN {test_auditor.catalog_name}.{test_auditor.schema_name} LIKE 'chat_interactions'"
                    st.info(f"Checking: {check_sql}")
                    check_result = test_auditor._execute_sql(check_sql)
                    if check_result.result and check_result.result.data_array:
                        st.success(f"✅ Table 'chat_interactions' exists!")
                        st.json({"tables_found": check_result.result.data_array})
                        
                        # Test querying the table
                        query_sql = f"SELECT COUNT(*) as row_count FROM {test_auditor.full_table_name}"
                        st.info(f"Querying: {query_sql}")
                        query_result = test_auditor._execute_sql(query_sql)
                        if query_result.result and query_result.result.data_array:
                            row_count = query_result.result.data_array[0][0]
                            st.success(f"✅ Table is queryable! Current rows: {row_count}")
                        
                    else:
                        st.error(f"❌ Table 'chat_interactions' not found after creation!")
                        
                except Exception as e:
                    st.error(f"❌ Table creation test failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Show current warehouse info
        if hasattr(test_auditor, 'warehouse') and test_auditor.warehouse:
            st.info(f"🏭 Using warehouse: {test_auditor.warehouse.name} (State: {test_auditor.warehouse.state})")
        else:
            st.warning("⚠️ No warehouse assigned to auditor")
                
    except Exception as sql_error:
        st.error(f"❌ SQL auditor initialization failed: {sql_error}")
        import traceback
        st.code(traceback.format_exc())
    
    # Check Simple Delta auditor
    st.subheader("🎯 Simple Delta Auditor Check")
    try:
        from simple_audit_utils import get_simple_auditor
        simple_auditor = get_simple_auditor()
        st.success("✅ Simple Delta auditor available")
        st.info(f"Table: {simple_auditor.full_table_name}")
        st.info(f"Databricks connected: {simple_auditor.databricks_connected}")
    except Exception as e:
        st.error(f"❌ Simple auditor failed: {e}")
    
    st.subheader("📦 Import Status")
    
    # Check if we're in Databricks environment
    st.subheader("🌐 Environment Check")
    databricks_env = os.getenv('DATABRICKS_RUNTIME_VERSION', 'Not detected')
    if databricks_env != 'Not detected':
        st.success(f"✅ Databricks Runtime: {databricks_env}")
    else:
        st.warning("⚠️ Not detected as Databricks environment")
    
    # Check compute availability
    compute_info = os.getenv('SPARK_HOME', 'Not set')
    st.info(f"Spark Home: {compute_info}")
    
    java_home = os.getenv('JAVA_HOME', 'Not set')  
    st.info(f"Java Home: {java_home}")
    try:
        from databricks.sdk import WorkspaceClient
        st.success("✅ databricks.sdk: Available")
    except ImportError as e:
        st.error(f"❌ databricks.sdk: {e}")
    
    try:
        from pyspark.sql import SparkSession
        st.success("✅ pyspark: Available")
        
        # Try to get/create Spark session
        try:
            spark = SparkSession.builder.appName("DiagnosticTest").getOrCreate()
            st.success(f"✅ Spark session: {spark.sparkContext.appName}")
            st.info(f"Spark master: {spark.sparkContext.master}")
            st.info(f"Spark version: {spark.version}")
        except Exception as spark_error:
            st.error(f"❌ Spark session failed: {spark_error}")
            
    except ImportError as e:
        st.error(f"❌ pyspark: {e}")
    
    try:
        from delta.tables import DeltaTable
        st.success("✅ delta-spark: Available")
    except ImportError as e:
        st.error(f"❌ delta-spark: {e}")
    
    # Now try the full diagnostics
    st.subheader("🔧 Full Diagnostics")
    try:
        from spark_diagnostics import diagnose_spark_environment, show_compute_recommendations
        diagnose_spark_environment()
        show_compute_recommendations()
    except Exception as e:
        st.error(f"Error loading full Spark diagnostics: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    st.stop()

# Add UCX-specific sidebar
with st.sidebar:
    st.header("🛠️ UCX Tools")
    
    if st.button("📋 Installation Checklist"):
        troubleshooter = UCXTroubleshooter()
        checklist = troubleshooter.get_installation_checklist()
        st.write("### Installation Checklist")
        for item in checklist:
            st.write(item)
        
        # Log checklist interaction
        auditor.log_interaction(
            session_id=st.session_state.session_id,
            user_info=user_info,
            user_question="Requested Installation Checklist",
            assistant_response=f"Provided {len(checklist)} installation checklist items",
            response_time_ms=0,
            endpoint_used="N/A",
            interaction_type="checklist",
            ucx_context_used=False
        )
    
    if st.button("🔍 Assessment Checklist"):
        troubleshooter = UCXTroubleshooter()
        checklist = troubleshooter.get_assessment_checklist()
        st.write("### Assessment Checklist")
        for item in checklist:
            st.write(item)
        
        # Log checklist interaction
        auditor.log_interaction(
            session_id=st.session_state.session_id,
            user_info=user_info,
            user_question="Requested Assessment Checklist",
            assistant_response=f"Provided {len(checklist)} assessment checklist items",
            response_time_ms=0,
            endpoint_used="N/A",
            interaction_type="checklist",
            ucx_context_used=False
        )
    
    if st.button("📚 Common Errors"):
        troubleshooter = UCXTroubleshooter()
        errors = troubleshooter.get_common_errors()
        st.write("### Common UCX Errors")
        for error_key, error_info in errors.items():
            with st.expander(f"🚨 {error_info['error']}"):
                st.write(f"**Solution:** {error_info['solution']}")
                st.write(f"**Details:** {error_info['details']}")
        
        # Log common errors interaction
        auditor.log_interaction(
            session_id=st.session_state.session_id,
            user_info=user_info,
            user_question="Requested Common Errors Guide",
            assistant_response=f"Provided {len(errors)} common error solutions",
            response_time_ms=0,
            endpoint_used="N/A",
            interaction_type="common_errors",
            ucx_context_used=False
        )

st.markdown(
    "💡 **UCX Troubleshooting Assistant** - Get help with Unity Catalog Migration issues, "
    "installation problems, and assessment errors. Just describe your issue and I'll provide specific guidance!"
)

# Check if endpoint is supported and show appropriate UI
if not endpoint_supported:
    st.error("⚠️ Unsupported Endpoint Type")
    st.markdown(
        f"The endpoint `{SERVING_ENDPOINT}` is not compatible with this basic chatbot template.\n\n"
        "This template only supports chat completions-compatible endpoints.\n\n"
        "👉 **For a richer chatbot template** that supports all conversational endpoints on Databricks, "
        "please see the [Databricks documentation](https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app)."
    )
else:
    st.info(
        "🔧 **UCX Expert Mode Activated!** This assistant specializes in Unity Catalog Migration troubleshooting. "
        "Ask about installation issues, assessment errors, or any UCX-related problems."
    )

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Use simplified format for assistant responses in history
                content = message["content"]
                
                # Show content with small download option
                col1, col2 = st.columns([9, 1])
                
                with col1:
                    # Show just summary in history, with expandable details
                    if len(content) > 300:
                        # Show first paragraph as summary
                        first_para = content.split('\n\n')[0] if content else ""
                        st.markdown(f'<div style="background:#f8f9fa;padding:8px;border-radius:4px;font-size:14px;line-height:1.3;margin:4px 0;">{first_para}</div>', unsafe_allow_html=True)
                        
                        with st.expander("View full details", expanded=False):
                            # Normalize headers in chat history 
                            normalized_content = content
                            normalized_content = normalized_content.replace('# ', '**')
                            normalized_content = normalized_content.replace('## ', '**')
                            normalized_content = normalized_content.replace('### ', '**')
                            normalized_content = normalized_content.replace('#### ', '**')
                            st.markdown(f'<div style="font-size:13px;line-height:1.5">{normalized_content}</div>', unsafe_allow_html=True)
                    else:
                        # For shorter responses, show normalized content directly
                        normalized_content = content
                        normalized_content = normalized_content.replace('# ', '**')
                        normalized_content = normalized_content.replace('## ', '**')
                        normalized_content = normalized_content.replace('### ', '**')
                        normalized_content = normalized_content.replace('#### ', '**')
                        st.markdown(f'<div style="font-size:14px;line-height:1.4">{normalized_content}</div>', unsafe_allow_html=True)
                
                with col2:
                    # Small download button for history items
                    history_key = f"history_download_{abs(hash(content))}"
                    
                    # Generate PDF for this historical response
                    if f"pdf_data_{history_key}" not in st.session_state:
                        try:
                            import io
                            from reportlab.lib.pagesizes import letter
                            from reportlab.lib.styles import getSampleStyleSheet
                            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                            
                            pdf_buffer = io.BytesIO()
                            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
                            styles = getSampleStyleSheet()
                            story = []
                            
                            story.append(Paragraph("UCX Troubleshooting Assistant Response", styles['Title']))
                            story.append(Spacer(1, 12))
                            story.append(Paragraph(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                            
                            # Clean and add content
                            clean_content = content.replace('**', '').replace('#', '').replace('*', '')
                            paragraphs = clean_content.split('\n\n')
                            for para in paragraphs:
                                if para.strip():
                                    story.append(Paragraph(para.strip(), styles['Normal']))
                            
                            doc.build(story)
                            st.session_state[f"pdf_data_{history_key}"] = pdf_buffer.getvalue()
                            pdf_buffer.close()
                        except:
                            st.session_state[f"pdf_data_{history_key}"] = None
                    
                    # Show download button if PDF is available
                    if st.session_state.get(f"pdf_data_{history_key}"):
                        st.download_button(
                            label="📄",
                            data=st.session_state[f"pdf_data_{history_key}"],
                            file_name=f"UCX_Response_History_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            help="Download this response as PDF",
                            key=history_key,
                            type="secondary"
                        )
            else:
                st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Describe your UCX issue or ask any Unity Catalog migration question..."):
        # Start timing for audit logging
        start_time = time.time()
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            # Create UCX-specific context for the query
            ucx_context = create_ucx_context(prompt)
            
            # Determine if UCX context was successfully created
            ucx_context_used = "UCX codebase cache not available" not in ucx_context
            
            # Detect error type from user prompt
            error_type_detected = None
            if any(keyword in prompt.lower() for keyword in ['error', 'fail', 'issue', 'problem', 'trouble']):
                # Try to classify the error type
                troubleshooter = UCXTroubleshooter()
                error_analysis = troubleshooter.analyze_error_message(prompt)
                error_type_detected = error_analysis.get('error', 'Unknown error')
            
            # Prepare messages with UCX context
            context_message = {
                "role": "system", 
                "content": ucx_context
            }
            
            # Combine context with conversation history
            messages_with_context = [context_message] + st.session_state.messages
            
            # Show prominent loading message while processing
            loading_placeholder = st.empty()
            with loading_placeholder.container():
                st.markdown("""
                <div style="
                    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    margin: 20px 0;
                    color: white;
                ">
                    <h2 style="margin: 0; color: white;">🤖 Processing Your Question...</h2>
                    <p style="margin: 10px 0; font-size: 16px;">UCX Assistant is analyzing your query and searching the knowledge base</p>
                    <div style="
                        width: 100%;
                        height: 6px;
                        background: rgba(255,255,255,0.3);
                        border-radius: 3px;
                        margin-top: 15px;
                        overflow: hidden;
                    ">
                        <div style="
                            width: 30%;
                            height: 100%;
                            background: white;
                            border-radius: 3px;
                            animation: loading 2s infinite;
                        "></div>
                    </div>
                </div>
                <style>
                @keyframes loading {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(400%); }
                }
                </style>
                """, unsafe_allow_html=True)
            
            try:
                # Query the Databricks serving endpoint
                assistant_response = query_endpoint(
                    endpoint_name=SERVING_ENDPOINT,
                    messages=messages_with_context,
                    max_tokens=600,
                )["content"]
            finally:
                # Clear the loading message once processing is complete
                loading_placeholder.empty()
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Apply privacy redaction to sensitive content
            safe_prompt = PrivacyManager.redact_sensitive_content(prompt)
            safe_response = PrivacyManager.redact_sensitive_content(assistant_response)
            
            # Log the interaction
            auditor.log_interaction(
                session_id=st.session_state.session_id,
                user_info=user_info,
                user_question=safe_prompt,
                assistant_response=safe_response,
                response_time_ms=response_time_ms,
                endpoint_used=SERVING_ENDPOINT,
                interaction_type="chat",
                ucx_context_used=ucx_context_used,
                error_type_detected=error_type_detected
            )
            
            # Generate Executive Summary with key bullet points
            def create_executive_summary(response):
                """Create a concise executive summary with key bullet points"""
                # Extract key points using pattern matching
                import re
                
                # Look for main points, issues, solutions, and steps
                key_points = []
                
                # Find numbered items, bullet points, or step-by-step items
                patterns = [
                    r'(?:^|\n)(?:\d+\.|Step \d+|[-*•])\s*(.+?)(?=\n(?:\d+\.|Step \d+|[-*•])|$)',
                    r'(?:Problem|Issue|Error|Solution|Fix|Reason|Cause):\s*(.+?)(?=\n|$)',
                    r'(?:^|\n)(.+?(?:error|fail|issue|problem|solution|fix|install|configure|enable).+?)(?=\n|$)'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        clean_point = match.strip().replace('\n', ' ')
                        if len(clean_point) > 20 and len(clean_point) < 150:  # Reasonable length
                            key_points.append(clean_point)
                
                # Remove duplicates and limit to top 4 points
                unique_points = list(dict.fromkeys(key_points))[:4]
                
                # If no structured points found, extract first few sentences
                if not unique_points:
                    sentences = response.split('. ')
                    unique_points = [s.strip() + '.' for s in sentences[:3] if len(s.strip()) > 20]
                
                return unique_points
            
            # Create executive summary
            key_points = create_executive_summary(assistant_response)
            
            # Executive Summary with bullet points
            st.markdown("**📋 Executive Summary**")
            if key_points:
                summary_html = '<div style="background:#f8f9fa;padding:12px;border-radius:6px;border-left:4px solid #0066cc;margin:8px 0 16px 0;font-size:14px;line-height:1.4;">'
                for point in key_points:
                    summary_html += f'• {point}<br>'
                summary_html += '</div>'
                st.markdown(summary_html, unsafe_allow_html=True)
            else:
                # Fallback to first paragraph
                first_para = assistant_response.split('\n\n')[0] if assistant_response else ""
                st.markdown(f'<div style="background:#f8f9fa;padding:12px;border-radius:6px;border-left:4px solid #0066cc;margin:8px 0 16px 0;font-size:14px;line-height:1.4;">{first_para}</div>', unsafe_allow_html=True)
            
            # Detailed Information - always expanded but with consistent formatting
            st.markdown("**📖 Detailed Information**")
            # Normalize headers and format consistently
            detailed_content = assistant_response
            detailed_content = detailed_content.replace('# ', '**')
            detailed_content = detailed_content.replace('## ', '**') 
            detailed_content = detailed_content.replace('### ', '**')
            detailed_content = detailed_content.replace('#### ', '**')
            
            st.markdown(f'<div style="font-size:13px;line-height:1.5;margin:8px 0;">{detailed_content}</div>', unsafe_allow_html=True)
            
            # PDF Download feature
            def create_pdf_content(question, response, key_points):
                """Create PDF content for download"""
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.units import inch
                    from datetime import datetime
                    import io
                    
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    
                    # Custom styles
                    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=12)
                    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=8)
                    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)
                    bullet_style = ParagraphStyle('CustomBullet', parent=styles['Normal'], fontSize=10, leftIndent=20, spaceAfter=4)
                    
                    story = []
                    
                    # Title
                    story.append(Paragraph("UCX Troubleshooting Assistant Response", title_style))
                    story.append(Spacer(1, 12))
                    
                    # Metadata
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    story.append(Paragraph(f"<b>Date:</b> {timestamp}", normal_style))
                    story.append(Paragraph(f"<b>Question:</b> {question}", normal_style))
                    story.append(Spacer(1, 12))
                    
                    # Executive Summary
                    story.append(Paragraph("Executive Summary", heading_style))
                    if key_points:
                        for point in key_points:
                            clean_point = point.replace('**', '<b>').replace('**', '</b>')
                            story.append(Paragraph(f"• {clean_point}", bullet_style))
                    else:
                        first_para = response.split('\n\n')[0] if response else ""
                        story.append(Paragraph(first_para, normal_style))
                    
                    story.append(Spacer(1, 12))
                    
                    # Detailed Information
                    story.append(Paragraph("Detailed Information", heading_style))
                    
                    # Clean and format the response for PDF
                    clean_response = response.replace('**', '<b>').replace('**', '</b>')
                    clean_response = clean_response.replace('# ', '').replace('## ', '').replace('### ', '')
                    
                    # Split into paragraphs and add to PDF
                    paragraphs = clean_response.split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            story.append(Paragraph(para.strip(), normal_style))
                    
                    story.append(Spacer(1, 24))
                    story.append(Paragraph("<i>Generated by UCX Troubleshooting Assistant</i>", normal_style))
                    
                    doc.build(story)
                    buffer.seek(0)
                    return buffer.getvalue()
                    
                except ImportError:
                    # Fallback: create a simple text-based PDF using HTML to PDF conversion
                    return create_simple_pdf_fallback(question, response, key_points)
            
            def create_simple_pdf_fallback(question, response, key_points):
                """Simple HTML-based PDF fallback"""
                from datetime import datetime
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                html_content = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        h1 {{ color: #333; }}
                        h2 {{ color: #666; margin-top: 20px; }}
                        .metadata {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
                        .summary {{ background: #e8f4f8; padding: 15px; border-radius: 5px; }}
                        ul {{ margin: 10px 0; }}
                        li {{ margin: 5px 0; }}
                    </style>
                </head>
                <body>
                    <h1>UCX Troubleshooting Assistant Response</h1>
                    
                    <div class="metadata">
                        <p><strong>Date:</strong> {timestamp}</p>
                        <p><strong>Question:</strong> {question}</p>
                    </div>
                    
                    <h2>Executive Summary</h2>
                    <div class="summary">
                        <ul>
                """
                
                if key_points:
                    for point in key_points:
                        html_content += f"<li>{point}</li>"
                else:
                    first_para = response.split('\n\n')[0] if response else ""
                    html_content += f"<li>{first_para}</li>"
                
                # Clean response for HTML
                clean_response = response.replace('**', '<strong>').replace('**', '</strong>')
                clean_response = clean_response.replace('\n', '<br>')
                
                html_content += f"""
                        </ul>
                    </div>
                    
                    <h2>Detailed Information</h2>
                    <div>{clean_response}</div>
                    
                    <hr>
                    <p><em>Generated by UCX Troubleshooting Assistant</em></p>
                </body>
                </html>
                """
                
                # Convert HTML to bytes (browsers can print this to PDF)
                return html_content.encode('utf-8')
            
            # Generate PDF content once and store in session state to prevent button disappearing
            pdf_session_key = f"pdf_data_{hash(assistant_response)}"
            
            if pdf_session_key not in st.session_state:
                try:
                    import io
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    
                    # Generate PDF content
                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    # Add content
                    story.append(Paragraph("UCX Troubleshooting Assistant Response", styles['Title']))
                    story.append(Spacer(1, 12))
                    story.append(Paragraph(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                    story.append(Paragraph(f"Question: {prompt}", styles['Normal']))
                    story.append(Spacer(1, 12))
                    
                    # Executive Summary
                    story.append(Paragraph("Executive Summary", styles['Heading2']))
                    if key_points:
                        for point in key_points:
                            clean_point = point.replace('**', '').replace('*', '')
                            story.append(Paragraph(f"• {clean_point}", styles['Normal']))
                    
                    story.append(Spacer(1, 12))
                    story.append(Paragraph("Detailed Information", styles['Heading2']))
                    
                    # Clean response for PDF
                    clean_response = assistant_response.replace('**', '').replace('#', '').replace('*', '')
                    paragraphs = clean_response.split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            story.append(Paragraph(para.strip(), styles['Normal']))
                    
                    doc.build(story)
                    st.session_state[pdf_session_key] = pdf_buffer.getvalue()
                    pdf_buffer.close()
                    
                except Exception as e:
                    st.session_state[pdf_session_key] = None
                    st.error(f"PDF generation failed: {e}")
            
            # Compact download section with persistent button
            if st.session_state.get(pdf_session_key):
                # Create a unique persistent key that won't change on rerun
                persistent_key = f"pdf_download_{abs(hash(assistant_response))}"
                
                # Mark this response as having a download available
                if f"has_download_{persistent_key}" not in st.session_state:
                    st.session_state[f"has_download_{persistent_key}"] = True
                
                st.markdown("---")
                
                # Compact download area
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    word_count = len(assistant_response.split())
                    st.markdown(f"**💾 Download available** • {word_count} words • Ready for customer documentation")
                
                with col2:
                    # Small icon-sized download button that persists
                    st.download_button(
                        label="📄",
                        data=st.session_state[pdf_session_key],
                        file_name=f"UCX_Response_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        help="Download PDF report",
                        key=persistent_key,
                        type="secondary"
                    )

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})

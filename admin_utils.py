"""
UCX Troubleshooting Assistant - Admin URL Generator

This utility helps generate secure admin URLs for accessing the audit dashboard.
"""

def generate_admin_url(base_url: str) -> str:
    """
    Generate admin URL for accessing the audit dashboard
    
    Args:
        base_url: Base URL of the Databricks app (without query parameters)
        
    Returns:
        Full admin URL with required query parameters
    """
    if base_url.endswith('/'):
        base_url = base_url.rstrip('/')
    
    return f"{base_url}?admin=dashboard"

def display_admin_instructions():
    """Display instructions for accessing the admin dashboard"""
    import streamlit as st
    
    with st.expander("🔒 Admin Dashboard Access", expanded=False):
        st.write("### How to Access the Audit Dashboard")
        
        st.info("""
        The audit dashboard is hidden from the main interface for security. 
        Only administrators with the special URL can access it.
        """)
        
        st.write("**To access the audit dashboard:**")
        st.code("https://your-app-url.databricksapps.com?admin=dashboard")
        
        st.write("**Example URLs:**")
        st.code("""
# Development
https://dev-ucx-doctor-{workspace-id}.1.azure.databricksapps.com?admin=dashboard

# Production  
https://prod-ucx-doctor-{workspace-id}.1.azure.databricksapps.com?admin=dashboard
        """)
        
        st.warning("🔐 **Security Note**: Only share this URL with authorized administrators.")
        
        st.write("**Features available in admin dashboard:**")
        st.markdown("""
        - 📊 **Real-time Analytics**: User interactions, response times, error patterns
        - 📈 **Interactive Charts**: Daily trends, hourly patterns, user activity
        - 🔍 **SQL Querying**: Custom analytics on audit data (Delta Lake mode)
        - 📤 **Data Export**: CSV/JSON downloads for compliance reporting
        - ⚙️ **Configuration**: Current audit table settings and validation
        """)

# Security configurations
ADMIN_ACCESS_CONFIG = {
    "url_parameter": "admin",
    "access_value": "dashboard", 
    "log_access": True,
    "require_databricks_auth": True
}

def is_admin_access_valid(query_params: dict) -> bool:
    """
    Validate admin access parameters
    
    Args:
        query_params: Dictionary of URL query parameters
        
    Returns:
        True if admin access is valid, False otherwise
    """
    return query_params.get(ADMIN_ACCESS_CONFIG["url_parameter"]) == ADMIN_ACCESS_CONFIG["access_value"]

# Example usage for deployment documentation
DEPLOYMENT_EXAMPLES = {
    "development": {
        "base_url": "https://dev-ucx-doctor-{workspace-id}.1.azure.databricksapps.com",
        "admin_url": "https://dev-ucx-doctor-{workspace-id}.1.azure.databricksapps.com?admin=dashboard"
    },
    "production": {
        "base_url": "https://prod-ucx-doctor-{workspace-id}.1.azure.databricksapps.com", 
        "admin_url": "https://prod-ucx-doctor-{workspace-id}.1.azure.databricksapps.com?admin=dashboard"
    }
}

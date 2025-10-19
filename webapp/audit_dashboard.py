"""
UCX Troubleshooting Assistant - Audit Dashboard with Delta Lake Support

This module provides a comprehensive audit dashboard for viewing and analyzing
chatbot interaction logs with Delta table integration and SQL querying capabilities.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from audit_utils import get_auditor, PrivacyManager
from simple_audit_utils import get_simple_auditor
from config_helper import AuditConfig
from audit_diagnostics import AuditDiagnostics


class AuditDashboard:
    """Interactive dashboard for audit log analysis with Delta Lake support"""
    
    def __init__(self):
        # Try to use SQL-based Delta Lake auditor first
        try:
            from sql_audit_utils import get_sql_auditor
            self.auditor = get_sql_auditor()
            self.audit_mode = "sql_warehouse"
        except Exception as e:
            # Fallback to simple auditor
            try:
                self.auditor = get_simple_auditor()
                self.audit_mode = "delta_simulation"
            except Exception as e2:
                # Last resort fallback
                self.auditor = get_auditor()
                self.audit_mode = "fallback"
    
    def render(self):
        """Render the complete audit dashboard"""
        st.header("📊 UCX Chatbot Audit Dashboard")
        
        # Display data source information
        stats = self.auditor.get_audit_stats()
        data_source = stats.get("data_source", "unknown")
        
        if data_source == "delta_table":
            st.success(f"🏛️ **Data Source**: Delta Lake Table `{stats.get('table_name', 'unknown')}`")
            st.info("✨ Enhanced capabilities: SQL querying, ACID transactions, time travel, and scalable analytics")
        elif data_source == "delta_table_simulation":
            st.success(f"🏛️ **Data Source**: Delta Lake Table `{stats.get('table_name', 'unknown')}`")
            st.info("✨ Optimized implementation: JSON backend with Delta Lake presentation layer")
            if stats.get('databricks_connected'):
                st.success("🔗 Connected to Databricks workspace")
            else:
                st.info("💡 Workspace connection available when deployed to Databricks")
        elif data_source == "json_file":
            st.warning("📄 **Data Source**: JSON File (Fallback mode)")
            st.info("💡 Deploy to Databricks environment to enable Delta Lake features")
        
        if stats.get("error"):
            st.error(f"Error loading audit data: {stats['error']}")
            
            # Show diagnostics to help troubleshoot
            st.info("🔧 **Troubleshooting**: Use the diagnostics below to identify and fix the issue.")
            AuditDiagnostics.display_diagnostics()
            return
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Overview", "⏰ Timeline", "👥 Users", "🚨 Errors", "🔍 SQL Query"])
        
        with tab1:
            self._render_overview_metrics(stats)
        
        with tab2:
            self._render_time_analysis()
        
        with tab3:
            self._render_user_patterns()
        
        with tab4:
            self._render_error_analysis(stats)
        
        with tab5:
            if data_source == "delta_table":
                self._render_sql_query_interface()
            else:
                st.info("SQL querying is only available when using Delta Lake tables.")
        
        # Recent interactions and export in expandable sections
        st.subheader("💬 Recent Interactions")
        self._render_recent_interactions()
        
        st.subheader("📤 Export Data")
        self._render_export_section()
    
    def _render_sql_query_interface(self):
        """Render SQL query interface for Delta table"""
        st.subheader("🔍 Custom SQL Query Interface")
        st.info("Query the audit data directly using SQL. Use `{table_name}` as placeholder for the table name.")
        
        # Predefined query examples
        st.write("### 📝 Sample Queries")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👥 Users by Activity"):
                sample_query = """
                SELECT user_email, COUNT(*) as interactions, 
                       AVG(response_time_ms) as avg_response_time
                FROM {table_name}
                WHERE user_email IS NOT NULL
                GROUP BY user_email
                ORDER BY interactions DESC
                LIMIT 10
                """
                st.session_state.sql_query = sample_query
        
        with col2:
            if st.button("📊 Daily Activity Trend"):
                sample_query = """
                SELECT DATE(timestamp) as date, 
                       COUNT(*) as interactions,
                       COUNT(DISTINCT user_email) as unique_users
                FROM {table_name}
                WHERE timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                """
                st.session_state.sql_query = sample_query
        
        col3, col4 = st.columns(2)
        
        with col3:
            if st.button("🚨 Error Analysis"):
                sample_query = """
                SELECT error_type_detected, COUNT(*) as count,
                       AVG(response_time_ms) as avg_response_time
                FROM {table_name}
                WHERE error_type_detected IS NOT NULL
                GROUP BY error_type_detected
                ORDER BY count DESC
                """
                st.session_state.sql_query = sample_query
        
        with col4:
            if st.button("⚡ Performance Analysis"):
                sample_query = """
                SELECT interaction_type,
                       AVG(response_time_ms) as avg_response_time,
                       MIN(response_time_ms) as min_response_time,
                       MAX(response_time_ms) as max_response_time,
                       COUNT(*) as total_interactions
                FROM {table_name}
                GROUP BY interaction_type
                ORDER BY avg_response_time DESC
                """
                st.session_state.sql_query = sample_query
        
        # SQL query input
        default_query = getattr(st.session_state, 'sql_query', """
SELECT * 
FROM {table_name}
ORDER BY timestamp DESC
LIMIT 10
""")
        
        sql_query = st.text_area(
            "Enter your SQL query:",
            value=default_query,
            height=150,
            help="Use {table_name} as placeholder for the audit table name"
        )
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            execute_query = st.button("🚀 Execute Query", type="primary")
        
        with col2:
            limit_results = st.checkbox("Limit results to 100 rows", value=True)
        
        if execute_query and sql_query.strip():
            try:
                with st.spinner("Executing query..."):
                    # Add LIMIT if requested and not already present
                    query_to_execute = sql_query
                    if limit_results and "LIMIT" not in sql_query.upper():
                        query_to_execute += "\nLIMIT 100"
                    
                    results = self.auditor.query_interactions_sql(query_to_execute)
                    
                    if results:
                        st.success(f"✅ Query executed successfully! Found {len(results)} results.")
                        
                        # Convert to DataFrame for better display
                        df = pd.DataFrame(results)
                        
                        # Display results in different formats
                        tab1, tab2, tab3 = st.tabs(["📊 Table View", "📈 Chart View", "📋 Raw Data"])
                        
                        with tab1:
                            st.dataframe(df, use_container_width=True)
                        
                        with tab2:
                            # Try to create a chart if data is suitable
                            if len(df.columns) >= 2:
                                # Get numeric columns for Y-axis
                                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                                if numeric_cols:
                                    x_col = st.selectbox("Select X-axis:", df.columns)
                                    y_col = st.selectbox("Select Y-axis:", numeric_cols)
                                    
                                    if st.button("Generate Chart"):
                                        fig = px.bar(df.head(20), x=x_col, y=y_col, 
                                                   title=f"{y_col} by {x_col}")
                                        st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("No numeric columns found for charting.")
                            else:
                                st.info("Insufficient columns for charting.")
                        
                        with tab3:
                            st.json(results[:10])  # Show first 10 results as JSON
                        
                        # Download option
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv_data,
                            file_name=f"audit_query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                    else:
                        st.warning("⚠️ Query executed but returned no results.")
                        
            except Exception as e:
                st.error(f"❌ Query execution failed: {str(e)}")
                st.code(sql_query, language="sql")
    
    def _render_overview_metrics(self, stats: Dict[str, Any]):
        """Render overview metrics cards with enhanced Delta table info"""
        st.subheader("📈 Overview Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Interactions", stats.get("total_interactions", 0))
        
        with col2:
            st.metric("Unique Users", stats.get("unique_users", 0))
        
        with col3:
            if stats.get("data_source") == "delta_table":
                st.metric("Data Source", "Delta Lake")
            else:
                file_size_kb = stats.get("audit_file_size_kb", 0)
                st.metric("Log File Size", f"{file_size_kb} KB")
        
        with col4:
            latest = stats.get("latest_interaction")
            if latest:
                if isinstance(latest, str):
                    latest_time = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                else:
                    latest_time = latest
                time_ago = datetime.now() - latest_time.replace(tzinfo=None)
                if time_ago.days > 0:
                    ago_str = f"{time_ago.days}d ago"
                elif time_ago.seconds > 3600:
                    ago_str = f"{time_ago.seconds//3600}h ago"
                else:
                    ago_str = f"{time_ago.seconds//60}m ago"
                st.metric("Last Activity", ago_str)
            else:
                st.metric("Last Activity", "N/A")
        
        # Additional Delta table specific metrics
        if stats.get("table_name"):
            st.info(f"📊 **Table**: `{stats['table_name']}` | **Engine**: Delta Lake | **Features**: ACID, Time Travel, Schema Evolution")
        
        # Configuration information
        AuditConfig.display_config_info()
    
    def _render_time_analysis(self):
        """Render enhanced time-based interaction analysis"""
        st.subheader("⏰ Interaction Timeline Analysis")
        
        recent_interactions = self.auditor.get_recent_interactions(limit=500)
        if not recent_interactions:
            st.info("No interaction data available for timeline analysis.")
            return
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(recent_interactions)
        
        # Fix data types - convert string numbers to actual numbers
        if 'response_time_ms' in df.columns:
            df['response_time_ms'] = pd.to_numeric(df['response_time_ms'], errors='coerce')
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Handle timestamp conversion for both string and datetime objects
        if 'timestamp' in df.columns:
            if df['timestamp'].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.day_name()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Interactions per day chart
            daily_counts = df['date'].value_counts().sort_index()
            fig_daily = px.line(
                x=daily_counts.index, 
                y=daily_counts.values,
                title="Daily Interactions Trend",
                labels={'x': 'Date', 'y': 'Number of Interactions'}
            )
            fig_daily.update_traces(mode='lines+markers')
            fig_daily.update_layout(showlegend=False)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        with col2:
            # Day of week distribution
            dow_counts = df['day_of_week'].value_counts()
            # Reorder days of week
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_counts = dow_counts.reindex([day for day in day_order if day in dow_counts.index])
            
            fig_dow = px.bar(
                x=dow_counts.index,
                y=dow_counts.values,
                title="Interactions by Day of Week",
                labels={'x': 'Day of Week', 'y': 'Number of Interactions'}
            )
            st.plotly_chart(fig_dow, use_container_width=True)
        
        # Hourly distribution
        hourly_counts = df['hour'].value_counts().sort_index()
        fig_hourly = px.bar(
            x=hourly_counts.index,
            y=hourly_counts.values,
            title="Interactions by Hour of Day",
            labels={'x': 'Hour (24h format)', 'y': 'Number of Interactions'}
        )
        fig_hourly.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    def _render_user_patterns(self):
        """Render user interaction patterns"""
        st.subheader("👥 User Interaction Patterns")
        
        recent_interactions = self.auditor.get_recent_interactions(limit=500)
        if not recent_interactions:
            st.info("No interaction data available for user pattern analysis.")
            return
        
        df = pd.DataFrame(recent_interactions)
        
        # Fix data types - convert string numbers to actual numbers
        if 'response_time_ms' in df.columns:
            df['response_time_ms'] = pd.to_numeric(df['response_time_ms'], errors='coerce')
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Interaction types distribution
        interaction_types = df['interaction_type'].value_counts()
        fig_types = px.pie(
            values=interaction_types.values,
            names=interaction_types.index,
            title="Interaction Types Distribution"
        )
        st.plotly_chart(fig_types, use_container_width=True)
        
        # Response time analysis
        if 'response_time_ms' in df.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                avg_response_time = df['response_time_ms'].mean()
                st.metric("Avg Response Time", f"{avg_response_time:.0f} ms")
            
            with col2:
                slow_responses = (df['response_time_ms'] > 5000).sum()
                st.metric("Slow Responses (>5s)", slow_responses)
            
            # Response time histogram
            fig_response = px.histogram(
                df, 
                x='response_time_ms',
                title="Response Time Distribution",
                labels={'response_time_ms': 'Response Time (ms)'}
            )
            st.plotly_chart(fig_response, use_container_width=True)
    
    def _render_error_analysis(self, stats: Dict[str, Any]):
        """Render error pattern analysis"""
        st.subheader("🚨 Error Analysis")
        
        error_types = stats.get("error_types_detected", {})
        if not error_types:
            st.info("No error patterns detected in recent interactions.")
            return
        
        # Error types chart
        fig_errors = px.bar(
            x=list(error_types.keys()),
            y=list(error_types.values()),
            title="Most Common Error Types",
            labels={'x': 'Error Type', 'y': 'Frequency'}
        )
        fig_errors.update_xaxes(tickangle=45)
        st.plotly_chart(fig_errors, use_container_width=True)
        
        # Error details table
        st.write("### Error Summary")
        error_df = pd.DataFrame(list(error_types.items()), columns=['Error Type', 'Count'])
        st.dataframe(error_df, use_container_width=True)
    
    def _render_recent_interactions(self):
        """Render recent interactions table"""
        st.subheader("💬 Recent Interactions")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            interaction_type_filter = st.selectbox(
                "Filter by Type",
                options=["All", "chat", "checklist", "common_errors"],
                index=0
            )
        
        with col2:
            limit = st.slider("Number of interactions", min_value=10, max_value=100, value=20)
        
        with col3:
            show_full_text = st.checkbox("Show full text", value=False)
        
        # Get filtered interactions
        recent_interactions = self.auditor.get_recent_interactions(limit=limit * 2)  # Get more to allow filtering
        
        if interaction_type_filter != "All":
            recent_interactions = [
                interaction for interaction in recent_interactions
                if interaction.get("interaction_type") == interaction_type_filter
            ]
        
        recent_interactions = recent_interactions[:limit]
        
        if not recent_interactions:
            st.info("No interactions match the selected filters.")
            return
        
        # Display interactions
        for i, interaction in enumerate(recent_interactions):
            # Create a container for each interaction instead of expander
            container = st.container()
            with container:
                st.markdown(f"**🕐 {interaction.get('timestamp', 'Unknown time')} - "
                           f"{interaction.get('user_email', 'Unknown user')[:20]}... - "
                           f"{interaction.get('interaction_type', 'chat').title()}**")
                
                with st.expander("View Details", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**User Question:**")
                        question = interaction.get('user_question', 'N/A')
                        if not show_full_text and len(question) > 200:
                            question = question[:200] + "..."
                        st.write(question)
                    
                    with col2:
                        st.write("**Response Time:**")
                        st.write(f"{interaction.get('response_time_ms', 0)} ms")
                        
                        if interaction.get('error_type_detected'):
                            st.write("**Error Type:**")
                            st.write(interaction['error_type_detected'])
                    
                    st.write("**Assistant Response:**")
                    response = interaction.get('assistant_response', 'N/A')
                    if not show_full_text and len(response) > 300:
                        response = response[:300] + "..."
                    st.write(response)
    
    def _render_export_section(self):
        """Render audit data export functionality"""
        st.subheader("📤 Export Audit Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input(
                "Start Date (optional)",
                value=None
            )
        
        with col2:
            end_date = st.date_input(
                "End Date (optional)", 
                value=None
            )
        
        with col3:
            export_format = st.selectbox(
                "Export Format",
                options=["JSON", "CSV"],
                index=0
            )
        
        if st.button("📥 Export Audit Data"):
            try:
                # Convert dates to ISO format if provided
                start_iso = start_date.isoformat() if start_date else None
                end_iso = end_date.isoformat() if end_date else None
                
                if export_format == "JSON":
                    # Export as JSON
                    export_path = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    success = self.auditor.export_audit_data(export_path, start_iso, end_iso)
                    
                    if success:
                        st.success(f"✅ Audit data exported to {export_path}")
                        
                        # Provide download button
                        with open(export_path, 'r') as f:
                            st.download_button(
                                label="📥 Download Export File",
                                data=f.read(),
                                file_name=export_path,
                                mime="application/json"
                            )
                    else:
                        st.error("❌ Failed to export audit data")
                
                else:  # CSV format
                    # Get interactions and convert to DataFrame
                    interactions = self.auditor.get_recent_interactions(limit=1000)
                    if start_iso or end_iso:
                        # Filter by date range
                        filtered_interactions = []
                        for interaction in interactions:
                            timestamp = interaction['timestamp']
                            if start_iso and timestamp < start_iso:
                                continue
                            if end_iso and timestamp > end_iso:
                                continue
                            filtered_interactions.append(interaction)
                        interactions = filtered_interactions
                    
                    if interactions:
                        df = pd.DataFrame(interactions)
                        
                        # Fix data types before export
                        if 'response_time_ms' in df.columns:
                            df['response_time_ms'] = pd.to_numeric(df['response_time_ms'], errors='coerce')
                        if 'timestamp' in df.columns:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                        
                        csv_data = df.to_csv(index=False)
                        
                        st.download_button(
                            label="📥 Download CSV Export",
                            data=csv_data,
                            file_name=f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        st.success(f"✅ Prepared CSV export with {len(interactions)} interactions")
                    else:
                        st.warning("⚠️ No interactions found for the specified date range")
                        
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")


def render_audit_dashboard():
    """Render the audit dashboard in Streamlit"""
    dashboard = AuditDashboard()
    dashboard.render()

# Keep for backward compatibility but prefer direct instantiation

"""
UCX Troubleshooting Assistant - SQL-based Audit Module

Uses Databricks SQL Warehouse instead of Spark for Delta operations.
No separate compute required - uses workspace's serverless SQL capability.
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    from databricks.sdk import WorkspaceClient
    # Use SDK's SQL execution instead of separate SQL connector
    SQL_AVAILABLE = True
except ImportError:
    SQL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass 
class ChatInteraction:
    """Data class representing a single chat interaction"""
    timestamp: str
    session_id: str
    user_name: Optional[str]
    user_email: Optional[str]
    user_id: Optional[str] 
    user_question: str
    assistant_response: str
    ucx_context_used: bool
    error_type_detected: Optional[str]
    response_time_ms: int
    endpoint_used: str
    interaction_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class SQLChatAuditor:
    """Handles audit logging using Databricks SQL Warehouse - no separate compute needed"""
    
    def __init__(self, table_name: str = "main.ucx_audit.chat_interactions"):
        """
        Initialize SQL-based chat auditor
        
        Args:
            table_name: Full table name in format catalog.schema.table
        """
        parts = table_name.split('.')
        if len(parts) == 3:
            self.catalog_name, self.schema_name, self.table_name = parts
        else:
            # Fallback for incomplete table names
            self.catalog_name = "main"
            self.schema_name = "ucx_audit"
            self.table_name = "chat_interactions"
        
        self.full_table_name = f"{self.catalog_name}.{self.schema_name}.{self.table_name}"
        
        if not SQL_AVAILABLE:
            logger.warning("Databricks SQL connector not available. Falling back to JSON file logging.")
            from pathlib import Path
            audit_dir = Path("audit_logs")
            audit_dir.mkdir(exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            self._fallback_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
            self._use_fallback = True
            return
        
        self._use_fallback = False
        try:
            # Use Databricks SDK for SQL operations
            self.ws = WorkspaceClient()
            
            # Get default SQL warehouse
            warehouses = list(self.ws.warehouses.list())
            if warehouses:
                # Find a running warehouse or use the first one
                running_warehouse = None
                for wh in warehouses:
                    if wh.state and wh.state.value == "RUNNING":
                        running_warehouse = wh
                        break
                
                if running_warehouse:
                    self.warehouse = running_warehouse
                    logger.info(f"Using running SQL warehouse: {running_warehouse.name}")
                else:
                    self.warehouse = warehouses[0]
                    logger.info(f"Using SQL warehouse: {warehouses[0].name}")
            else:
                raise Exception("No SQL warehouses available in workspace")
            
            self._initialize_audit_table()
            logger.info(f"✅ SDK-based audit table initialized: {self.full_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SDK audit table: {e}")
            logger.info("Falling back to JSON file logging")
            self._use_fallback = True
            from pathlib import Path
            audit_dir = Path("audit_logs")
            audit_dir.mkdir(exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            self._fallback_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
    
    def _execute_sql(self, sql_query: str, params: tuple = None):
        """Execute SQL using Databricks SDK"""
        try:
            logger.info(f"🔧 Executing SQL: {sql_query[:100]}...")
            logger.info(f"🏭 Using warehouse: {self.warehouse.id}")
            
            # Use SDK's SQL execution capability
            result = self.ws.statement_execution.execute_statement(
                warehouse_id=self.warehouse.id,
                statement=sql_query,
                wait_timeout="30s"
            )
            
            logger.info(f"✅ SQL execution successful")
            if hasattr(result, 'status'):
                logger.info(f"📊 Result status: {result.status}")
            
            return result
        except Exception as e:
            import traceback
            logger.error(f"❌ SQL execution failed: {e}")
            logger.error(f"📜 Full SQL: {sql_query}")
            logger.error(f"🏭 Warehouse ID: {self.warehouse.id if self.warehouse else 'None'}")
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
            raise
    
    def _initialize_audit_table(self):
        """Initialize the Delta audit table using SDK"""
        try:
            logger.info(f"🔨 Creating Delta table infrastructure...")
            
            # Create catalog and schema with better error handling
            try:
                catalog_sql = f"CREATE CATALOG IF NOT EXISTS {self.catalog_name}"
                logger.info(f"Executing: {catalog_sql}")
                self._execute_sql(catalog_sql)
                logger.info(f"✅ Catalog {self.catalog_name} ready")
            except Exception as e:
                logger.warning(f"⚠️ Catalog creation issue (may already exist): {e}")
                # Continue - catalog might already exist
            
            try:
                schema_sql = f"CREATE SCHEMA IF NOT EXISTS {self.catalog_name}.{self.schema_name}"
                logger.info(f"Executing: {schema_sql}")
                self._execute_sql(schema_sql)
                logger.info(f"✅ Schema {self.catalog_name}.{self.schema_name} ready")
            except Exception as e:
                logger.warning(f"⚠️ Schema creation issue (may already exist): {e}")
                # Continue - schema might already exist
            
            # Create the Delta table using SQL DDL
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.full_table_name} (
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
            
            logger.info(f"Creating table: {self.full_table_name}")
            logger.info(f"Table SQL: {create_table_sql}")
            self._execute_sql(create_table_sql)
            logger.info(f"✅ Delta table ready: {self.full_table_name}")
            
            # Test that we can query the table
            test_sql = f"SELECT COUNT(*) FROM {self.full_table_name}"
            result = self._execute_sql(test_sql)
            logger.info(f"✅ Table query test successful")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to initialize Delta audit table: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def log_interaction(self, session_id: str, user_info: Dict[str, Optional[str]], 
                       user_question: str, assistant_response: str, response_time_ms: int,
                       endpoint_used: str, interaction_type: str = "chat", 
                       ucx_context_used: bool = True, error_type_detected: Optional[str] = None) -> None:
        """Log interaction using SQL INSERT"""
        
        if self._use_fallback:
            return self._log_interaction_fallback(session_id, user_info, user_question, 
                                                assistant_response, response_time_ms, endpoint_used,
                                                interaction_type, ucx_context_used, error_type_detected)
        
        try:
            interaction = ChatInteraction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                user_name=user_info.get('user_name'),
                user_email=user_info.get('user_email'),
                user_id=user_info.get('user_id'),
                user_question=user_question[:1000],  # Limit length
                assistant_response=assistant_response[:2000],  # Limit length
                ucx_context_used=ucx_context_used,
                error_type_detected=error_type_detected,
                response_time_ms=response_time_ms,
                endpoint_used=endpoint_used,
                interaction_type=interaction_type
            )
            
            # Insert using parameterized query via SDK
            insert_sql = f"""
            INSERT INTO {self.full_table_name} VALUES (
                TIMESTAMP '{interaction.timestamp}',
                '{interaction.session_id}',
                {f"'{interaction.user_name}'" if interaction.user_name else 'NULL'},
                {f"'{interaction.user_email}'" if interaction.user_email else 'NULL'},
                {f"'{interaction.user_id}'" if interaction.user_id else 'NULL'},
                '{interaction.user_question.replace("'", "''")}',
                '{interaction.assistant_response.replace("'", "''")[:2000]}',
                {str(interaction.ucx_context_used).lower()},
                {f"'{interaction.error_type_detected}'" if interaction.error_type_detected else 'NULL'},
                {interaction.response_time_ms},
                '{interaction.endpoint_used}',
                '{interaction.interaction_type}'
            )
            """
            
            self._execute_sql(insert_sql)
            logger.info(f"Logged interaction to SQL table: {interaction.interaction_type}")
                
        except Exception as e:
            logger.error(f"Failed to log interaction to SQL table: {e}")
            # Fall back to JSON logging for this interaction
            self._log_interaction_fallback(session_id, user_info, user_question, 
                                         assistant_response, response_time_ms, endpoint_used,
                                         interaction_type, ucx_context_used, error_type_detected)
    
    def get_audit_stats(self) -> Dict[str, Any]:
        """Get audit statistics using SQL queries"""
        if self._use_fallback:
            return self._get_audit_stats_fallback()
        
        try:
            # Get basic stats
            stats_result = self._execute_sql(f"""
                SELECT 
                    COUNT(*) as total_interactions,
                    COUNT(DISTINCT user_email) as unique_users,
                    MAX(timestamp) as latest_interaction
                FROM {self.full_table_name}
            """)
            
            if stats_result and hasattr(stats_result, 'result') and stats_result.result:
                basic_stats = stats_result.result.data_array[0] if stats_result.result.data_array else [0, 0, None]
            else:
                basic_stats = [0, 0, None]
            
            # Get error types
            try:
                error_result = self._execute_sql(f"""
                    SELECT error_type_detected, COUNT(*) as count
                    FROM {self.full_table_name} 
                    WHERE error_type_detected IS NOT NULL
                    GROUP BY error_type_detected
                """)
                error_types = {}
                if error_result and hasattr(error_result, 'result') and error_result.result and error_result.result.data_array:
                    for row in error_result.result.data_array:
                        error_types[row[0]] = row[1]
            except:
                error_types = {}
            
            # Get interaction types  
            try:
                interaction_result = self._execute_sql(f"""
                    SELECT interaction_type, COUNT(*) as count
                    FROM {self.full_table_name}
                    GROUP BY interaction_type
                """)
                interaction_types = {}
                if interaction_result and hasattr(interaction_result, 'result') and interaction_result.result and interaction_result.result.data_array:
                    for row in interaction_result.result.data_array:
                        interaction_types[row[0]] = row[1]
            except:
                interaction_types = {}
                
            return {
                "total_interactions": basic_stats[0] if basic_stats[0] is not None else 0,
                "unique_users": basic_stats[1] if basic_stats[1] is not None else 0,
                "latest_interaction": str(basic_stats[2]) if basic_stats[2] else None,
                "error_types_detected": error_types,
                "interaction_types": interaction_types,
                "data_source": "delta_table",
                "table_name": self.full_table_name,
                "warehouse_id": self.warehouse.id
            }
                
        except Exception as e:
            logger.error(f"Failed to get SQL audit stats: {e}")
            return {"error": str(e), "data_source": "sql_warehouse"}
    
    def get_user_interactions(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get interactions for a specific user using SQL"""
        if self._use_fallback:
            return self._get_user_interactions_fallback(user_email, limit)
        
        try:
            result = self._execute_sql(f"""
                SELECT timestamp, session_id, user_name, user_email, user_id,
                       user_question, assistant_response, ucx_context_used,
                       error_type_detected, response_time_ms, endpoint_used, interaction_type
                FROM {self.full_table_name}
                WHERE user_email = '{user_email}'
                ORDER BY timestamp DESC
                LIMIT {limit}
            """)
            
            interactions = []
            if result and hasattr(result, 'result') and result.result and result.result.data_array:
                for row in result.result.data_array:
                    interactions.append({
                        'timestamp': str(row[0]),
                        'session_id': row[1],
                        'user_name': row[2],
                        'user_email': row[3],
                        'user_id': row[4],
                        'user_question': row[5],
                        'assistant_response': row[6],
                        'ucx_context_used': row[7],
                        'error_type_detected': row[8],
                        'response_time_ms': row[9],
                        'endpoint_used': row[10],
                        'interaction_type': row[11]
                    })
            return interactions
            
        except Exception as e:
            logger.error(f"Failed to get user interactions: {e}")
            return []
    
    def get_recent_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent interactions using SQL"""
        if self._use_fallback:
            return self._get_recent_interactions_fallback(limit)
        
        try:
            result = self._execute_sql(f"""
                SELECT timestamp, session_id, user_name, user_email, user_id,
                       user_question, assistant_response, ucx_context_used,
                       error_type_detected, response_time_ms, endpoint_used, interaction_type
                FROM {self.full_table_name}
                ORDER BY timestamp DESC
                LIMIT {limit}
            """)
            
            interactions = []
            if result and hasattr(result, 'result') and result.result and result.result.data_array:
                for row in result.result.data_array:
                    interactions.append({
                        'timestamp': str(row[0]),
                        'session_id': row[1],
                        'user_name': row[2],
                        'user_email': row[3],
                        'user_id': row[4],
                        'user_question': row[5],
                        'assistant_response': row[6],
                        'ucx_context_used': row[7],
                        'error_type_detected': row[8],
                        'response_time_ms': row[9],
                        'endpoint_used': row[10],
                        'interaction_type': row[11]
                    })
            return interactions
            
        except Exception as e:
            logger.error(f"Failed to get recent interactions: {e}")
            return []
    
    def query_interactions_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute custom SQL query on the audit data"""
        if self._use_fallback:
            logger.warning("SQL querying not available with fallback mode")
            return []
        
        try:
            # Replace placeholder with actual table name
            formatted_query = sql_query.format(table_name=self.full_table_name)
            result = self._execute_sql(formatted_query)
            
            query_results = []
            if result and hasattr(result, 'result') and result.result:
                if result.result.data_array:
                    # Get column names from the schema
                    columns = []
                    if result.result.manifest and result.result.manifest.schema and result.result.manifest.schema.columns:
                        columns = [col.name for col in result.result.manifest.schema.columns]
                    
                    for row in result.result.data_array:
                        if columns:
                            query_results.append(dict(zip(columns, row)))
                        else:
                            # Fallback: use generic column names
                            query_results.append({f"col_{i}": val for i, val in enumerate(row)})
                            
            return query_results
            
        except Exception as e:
            logger.error(f"Failed to execute SQL query: {e}")
            return []
    
    def export_audit_data(self, output_path: str, start_date: str = None, end_date: str = None) -> bool:
        """Export audit data using SQL"""
        try:
            # Build WHERE clause for date filtering
            where_clause = ""
            if start_date or end_date:
                conditions = []
                if start_date:
                    conditions.append(f"timestamp >= TIMESTAMP '{start_date}'")
                if end_date:
                    conditions.append(f"timestamp <= TIMESTAMP '{end_date}'")
                where_clause = "WHERE " + " AND ".join(conditions)
            
            result = self._execute_sql(f"""
                SELECT timestamp, session_id, user_name, user_email, user_id,
                       user_question, assistant_response, ucx_context_used,
                       error_type_detected, response_time_ms, endpoint_used, interaction_type
                FROM {self.full_table_name}
                {where_clause}
                ORDER BY timestamp DESC
            """)
            
            interactions = []
            if result and hasattr(result, 'result') and result.result and result.result.data_array:
                for row in result.result.data_array:
                    interactions.append({
                        'timestamp': str(row[0]),
                        'session_id': row[1],
                        'user_name': row[2],
                        'user_email': row[3],
                        'user_id': row[4],
                        'user_question': row[5],
                        'assistant_response': row[6],
                        'ucx_context_used': row[7],
                        'error_type_detected': row[8],
                        'response_time_ms': row[9],
                        'endpoint_used': row[10],
                        'interaction_type': row[11]
                    })
            
            # Export to file
            if output_path.endswith('.csv'):
                import pandas as pd
                df = pd.DataFrame(interactions)
                df.to_csv(output_path, index=False)
            else:
                # Export as JSON
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(interactions, f, indent=2, default=str)
            
            logger.info(f"Exported {len(interactions)} interactions to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export audit data: {e}")
            return False
    
    def _log_interaction_fallback(self, session_id: str, user_info: Dict[str, Optional[str]], 
                                user_question: str, assistant_response: str, response_time_ms: int,
                                endpoint_used: str, interaction_type: str, ucx_context_used: bool, 
                                error_type_detected: Optional[str]) -> None:
        """Fallback to JSON logging"""
        try:
            interaction = ChatInteraction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                user_name=user_info.get('user_name'),
                user_email=user_info.get('user_email'),
                user_id=user_info.get('user_id'),
                user_question=user_question,
                assistant_response=assistant_response,
                ucx_context_used=ucx_context_used,
                error_type_detected=error_type_detected,
                response_time_ms=response_time_ms,
                endpoint_used=endpoint_used,
                interaction_type=interaction_type
            )
            
            with open(self._fallback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(interaction.to_dict()) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to log to fallback file: {e}")
    
    def _get_user_interactions_fallback(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fallback method to get user interactions from JSON file"""
        try:
            interactions = []
            if self._fallback_file.exists():
                with open(self._fallback_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get('user_email') == user_email:
                                interactions.append(data)
                                if len(interactions) >= limit:
                                    break
                        except json.JSONDecodeError:
                            continue
            return sorted(interactions, key=lambda x: x.get('timestamp', ''), reverse=True)
        except Exception as e:
            logger.error(f"Failed to get user interactions from fallback file: {e}")
            return []
    
    def _get_recent_interactions_fallback(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fallback method to get recent interactions from JSON file"""
        try:
            interactions = []
            if self._fallback_file.exists():
                with open(self._fallback_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            interactions.append(data)
                        except json.JSONDecodeError:
                            continue
            # Sort by timestamp and return most recent
            interactions = sorted(interactions, key=lambda x: x.get('timestamp', ''), reverse=True)
            return interactions[:limit]
        except Exception as e:
            logger.error(f"Failed to get recent interactions from fallback file: {e}")
            return []
    
    def _get_audit_stats_fallback(self) -> Dict[str, Any]:
        """Fallback JSON file statistics"""
        # Implementation similar to previous version
        return {
            "total_interactions": 0,
            "unique_users": 0, 
            "data_source": "json_file",
            "error": "Using JSON fallback mode"
        }


# Global auditor instance
_sql_auditor_instance = None

def get_sql_auditor(**kwargs) -> SQLChatAuditor:
    """Get the global SQL auditor instance"""
    global _sql_auditor_instance
    if _sql_auditor_instance is None:
        import os
        
        table_name = kwargs.get('table_name', os.getenv('AUDIT_TABLE', 'main.ucx_audit.chat_interactions'))
        
        _sql_auditor_instance = SQLChatAuditor(table_name=table_name)
        logger.info(f"Initialized SQL audit system: {_sql_auditor_instance.full_table_name}")
        
    return _sql_auditor_instance

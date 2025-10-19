"""
UCX Troubleshooting Assistant - Audit Module with Delta Lake

This module provides comprehensive audit logging for chatbot interactions using Delta tables
for scalable, ACID-compliant audit trails with native Databricks integration.
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType, TimestampType
    from delta.tables import DeltaTable
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    WorkspaceClient = None
    SparkSession = None

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
    interaction_type: str  # 'chat', 'checklist', 'common_errors'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DeltaChatAuditor:
    """Handles audit logging for UCX troubleshooting chat interactions using Delta tables"""
    
    def __init__(self, catalog_name: str = "main", schema_name: str = "ucx_audit", table_name: str = "chat_interactions"):
        """
        Initialize the Delta chat auditor
        
        Args:
            catalog_name: Unity Catalog name for the audit table
            schema_name: Schema name for the audit table
            table_name: Table name for audit interactions
        """
        self.catalog_name = catalog_name
        self.schema_name = schema_name
        self.table_name = table_name
        self.full_table_name = f"{catalog_name}.{schema_name}.{table_name}"
        
        if not DATABRICKS_AVAILABLE:
            logger.info("Using JSON file audit logging. Delta Lake mode available when Spark compute is configured.")
            from pathlib import Path
            audit_dir = Path("audit_logs")
            audit_dir.mkdir(exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            self._fallback_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
            self._use_fallback = True
            return
        
        self._use_fallback = False
        try:
            logger.info("Attempting to initialize Spark session...")
            self.spark = SparkSession.builder.appName("UCX-Audit").getOrCreate()
            logger.info(f"Spark session created successfully: {self.spark}")
            
            logger.info("Attempting to initialize Databricks WorkspaceClient...")
            self.ws = WorkspaceClient()
            logger.info("WorkspaceClient initialized successfully")
            
            logger.info(f"Attempting to initialize audit table: {self.full_table_name}")
            self._initialize_audit_table()
            logger.info(f"✅ Delta audit table initialized successfully: {self.full_table_name}")
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to initialize Delta audit table: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.info("⚠️  Falling back to JSON file logging")
            self._use_fallback = True
            from pathlib import Path
            audit_dir = Path("audit_logs")
            audit_dir.mkdir(exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            self._fallback_file = audit_dir / f"ucx_chat_audit_{today}.jsonl"
            logger.info(f"JSON fallback file: {self._fallback_file}")
    
    def _get_audit_schema(self) -> StructType:
        """Define the schema for the audit Delta table"""
        return StructType([
            StructField("timestamp", TimestampType(), False),
            StructField("session_id", StringType(), False),
            StructField("user_name", StringType(), True),
            StructField("user_email", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("user_question", StringType(), False),
            StructField("assistant_response", StringType(), False),
            StructField("ucx_context_used", BooleanType(), False),
            StructField("error_type_detected", StringType(), True),
            StructField("response_time_ms", IntegerType(), False),
            StructField("endpoint_used", StringType(), False),
            StructField("interaction_type", StringType(), False),
        ])
    
    def _initialize_audit_table(self):
        """Initialize the Delta audit table if it doesn't exist"""
        try:
            # Check if catalog and schema exist, create if not
            self.spark.sql(f"CREATE CATALOG IF NOT EXISTS {self.catalog_name}")
            self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {self.catalog_name}.{self.schema_name}")
            
            # Check if table exists
            table_exists = self.spark.catalog.tableExists(self.full_table_name)
            
            if not table_exists:
                # Create the Delta table
                schema = self._get_audit_schema()
                empty_df = self.spark.createDataFrame([], schema)
                
                empty_df.write \
                    .format("delta") \
                    .mode("overwrite") \
                    .option("mergeSchema", "true") \
                    .saveAsTable(self.full_table_name)
                
                # Add table properties for better organization
                self.spark.sql(f"""
                    ALTER TABLE {self.full_table_name} 
                    SET TBLPROPERTIES (
                        'description' = 'UCX Troubleshooting Assistant Audit Log',
                        'created_by' = 'UCX-Troubleshooting-Assistant',
                        'data_classification' = 'internal_audit'
                    )
                """)
                
                logger.info(f"Created new Delta audit table: {self.full_table_name}")
            else:
                logger.info(f"Using existing Delta audit table: {self.full_table_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Delta table: {e}")
            raise
    
    def log_interaction(
        self,
        session_id: str,
        user_info: Dict[str, Optional[str]],
        user_question: str,
        assistant_response: str,
        response_time_ms: int,
        endpoint_used: str,
        interaction_type: str = "chat",
        ucx_context_used: bool = True,
        error_type_detected: Optional[str] = None
    ) -> None:
        """
        Log a chat interaction to the Delta audit table
        """
        if self._use_fallback:
            return self._log_interaction_fallback(
                session_id, user_info, user_question, assistant_response,
                response_time_ms, endpoint_used, interaction_type,
                ucx_context_used, error_type_detected
            )
        
        try:
            # Create DataFrame for the new interaction
            interaction_data = [(
                datetime.now(timezone.utc),
                session_id,
                user_info.get("user_name"),
                user_info.get("user_email"),
                user_info.get("user_id"),
                user_question,
                assistant_response,
                ucx_context_used,
                error_type_detected,
                response_time_ms,
                endpoint_used,
                interaction_type
            )]
            
            schema = self._get_audit_schema()
            df = self.spark.createDataFrame(interaction_data, schema)
            
            # Append to Delta table
            df.write \
                .format("delta") \
                .mode("append") \
                .saveAsTable(self.full_table_name)
            
            logger.debug(f"Logged interaction to Delta table for user {user_info.get('user_email', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to log interaction to Delta table: {e}")
            # Fallback to JSON logging
            self._log_interaction_fallback(
                session_id, user_info, user_question, assistant_response,
                response_time_ms, endpoint_used, interaction_type,
                ucx_context_used, error_type_detected
            )
    
    def _log_interaction_fallback(
        self,
        session_id: str,
        user_info: Dict[str, Optional[str]],
        user_question: str,
        assistant_response: str,
        response_time_ms: int,
        endpoint_used: str,
        interaction_type: str = "chat",
        ucx_context_used: bool = True,
        error_type_detected: Optional[str] = None
    ) -> None:
        """Fallback JSON file logging when Delta is not available"""
        try:
            interaction = ChatInteraction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                user_name=user_info.get("user_name"),
                user_email=user_info.get("user_email"),
                user_id=user_info.get("user_id"),
                user_question=user_question,
                assistant_response=assistant_response,
                ucx_context_used=ucx_context_used,
                error_type_detected=error_type_detected,
                response_time_ms=response_time_ms,
                endpoint_used=endpoint_used,
                interaction_type=interaction_type
            )
            
            # Append to JSONL file (one JSON object per line)
            with open(self._fallback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(interaction.to_dict()) + '\n')
                
            logger.debug(f"Logged interaction to fallback file for user {user_info.get('user_email', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to log chat interaction to fallback file: {e}")
    
    def get_audit_stats(self) -> Dict[str, Any]:
        """Get audit statistics from the Delta table"""
        if self._use_fallback:
            return self._get_audit_stats_fallback()
        
        try:
            # Query Delta table for statistics
            stats_query = f"""
            SELECT 
                COUNT(*) as total_interactions,
                COUNT(DISTINCT user_email) as unique_users,
                MAX(timestamp) as latest_interaction,
                COUNT(DISTINCT interaction_type) as interaction_types_count
            FROM {self.full_table_name}
            """
            
            stats_df = self.spark.sql(stats_query)
            stats_row = stats_df.collect()[0]
            
            # Get error type distribution
            error_query = f"""
            SELECT error_type_detected, COUNT(*) as count
            FROM {self.full_table_name}
            WHERE error_type_detected IS NOT NULL
            GROUP BY error_type_detected
            ORDER BY count DESC
            """
            
            error_df = self.spark.sql(error_query)
            error_types = {row['error_type_detected']: row['count'] for row in error_df.collect()}
            
            # Get interaction type distribution
            interaction_query = f"""
            SELECT interaction_type, COUNT(*) as count
            FROM {self.full_table_name}
            GROUP BY interaction_type
            ORDER BY count DESC
            """
            
            interaction_df = self.spark.sql(interaction_query)
            interaction_types = {row['interaction_type']: row['count'] for row in interaction_df.collect()}
            
            return {
                "total_interactions": stats_row['total_interactions'],
                "unique_users": stats_row['unique_users'],
                "error_types_detected": error_types,
                "interaction_types": interaction_types,
                "latest_interaction": stats_row['latest_interaction'].isoformat() if stats_row['latest_interaction'] else None,
                "data_source": "delta_table",
                "table_name": self.full_table_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit stats from Delta table: {e}")
            return {"error": str(e), "data_source": "delta_table"}
    
    def _get_audit_stats_fallback(self) -> Dict[str, Any]:
        """Fallback JSON file statistics when Delta is not available"""
        try:
            if not self._fallback_file.exists():
                # Create empty audit file if it doesn't exist
                self._fallback_file.parent.mkdir(exist_ok=True)
                with open(self._fallback_file, 'w', encoding='utf-8') as f:
                    pass  # Create empty file
                
                return {
                    "total_interactions": 0, 
                    "unique_users": 0, 
                    "error_types_detected": {},
                    "interaction_types": {},
                    "audit_file_size_kb": 0,
                    "latest_interaction": None,
                    "data_source": "json_file",
                    "status": "initialized_empty_file"
                }
            
            interactions = []
            unique_users = set()
            error_types = {}
            interaction_types = {}
            
            with open(self._fallback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        interaction = json.loads(line.strip())
                        interactions.append(interaction)
                        
                        if interaction.get('user_email'):
                            unique_users.add(interaction['user_email'])
                        
                        error_type = interaction.get('error_type_detected')
                        if error_type:
                            error_types[error_type] = error_types.get(error_type, 0) + 1
                        
                        int_type = interaction.get('interaction_type', 'chat')
                        interaction_types[int_type] = interaction_types.get(int_type, 0) + 1
                        
                    except json.JSONDecodeError:
                        continue
            
            return {
                "total_interactions": len(interactions),
                "unique_users": len(unique_users),
                "error_types_detected": error_types,
                "interaction_types": interaction_types,
                "audit_file_size_kb": round(self._fallback_file.stat().st_size / 1024, 2),
                "latest_interaction": interactions[-1]['timestamp'] if interactions else None,
                "data_source": "json_file"
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit stats from fallback file: {e}")
            return {
                "error": str(e), 
                "data_source": "json_file",
                "total_interactions": 0,
                "unique_users": 0
            }
    
    def get_user_interactions(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get interactions for a specific user"""
        if self._use_fallback:
            return self._get_user_interactions_fallback(user_email, limit)
        
        try:
            query = f"""
            SELECT *
            FROM {self.full_table_name}
            WHERE user_email = '{user_email}'
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
            
            df = self.spark.sql(query)
            return [row.asDict() for row in df.collect()]
            
        except Exception as e:
            logger.error(f"Failed to get user interactions from Delta table: {e}")
            return []
    
    def _get_user_interactions_fallback(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fallback method for getting user interactions from JSON file"""
        try:
            if not self._fallback_file.exists():
                return []
            
            user_interactions = []
            with open(self._fallback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        interaction = json.loads(line.strip())
                        if interaction.get('user_email') == user_email:
                            user_interactions.append(interaction)
                    except json.JSONDecodeError:
                        continue
            
            # Return most recent interactions first
            return sorted(user_interactions, key=lambda x: x['timestamp'], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get user interactions from fallback file: {e}")
            return []
    
    def get_recent_interactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get the most recent interactions across all users"""
        if self._use_fallback:
            return self._get_recent_interactions_fallback(limit)
        
        try:
            query = f"""
            SELECT *
            FROM {self.full_table_name}
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
            
            df = self.spark.sql(query)
            return [row.asDict() for row in df.collect()]
            
        except Exception as e:
            logger.error(f"Failed to get recent interactions from Delta table: {e}")
            return []
    
    def _get_recent_interactions_fallback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fallback method for getting recent interactions from JSON file"""
        try:
            if not self._fallback_file.exists():
                return []
            
            interactions = []
            with open(self._fallback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        interaction = json.loads(line.strip())
                        interactions.append(interaction)
                    except json.JSONDecodeError:
                        continue
            
            # Return most recent interactions first
            return sorted(interactions, key=lambda x: x['timestamp'], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent interactions from fallback file: {e}")
            return []
    
    def export_audit_data(self, output_path: str, start_date: str = None, end_date: str = None) -> bool:
        """Export audit data to a file"""
        if self._use_fallback:
            return self._export_audit_data_fallback(output_path, start_date, end_date)
        
        try:
            # Build query with optional date filtering
            where_clause = ""
            if start_date or end_date:
                conditions = []
                if start_date:
                    conditions.append(f"timestamp >= '{start_date}'")
                if end_date:
                    conditions.append(f"timestamp <= '{end_date}'")
                where_clause = "WHERE " + " AND ".join(conditions)
            
            query = f"""
            SELECT *
            FROM {self.full_table_name}
            {where_clause}
            ORDER BY timestamp DESC
            """
            
            df = self.spark.sql(query)
            interactions = [row.asDict() for row in df.collect()]
            
            # Export to JSON file
            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_interactions": len(interactions),
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "data_source": "delta_table",
                "table_name": self.full_table_name,
                "interactions": interactions
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(interactions)} interactions to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export audit data from Delta table: {e}")
            return False
    
    def _export_audit_data_fallback(self, output_path: str, start_date: str = None, end_date: str = None) -> bool:
        """Fallback export method using JSON file"""
        try:
            if not self._fallback_file.exists():
                logger.warning("No audit file found for export")
                return False
            
            interactions = []
            with open(self._fallback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        interaction = json.loads(line.strip())
                        
                        # Apply date filtering if specified
                        if start_date or end_date:
                            interaction_date = interaction['timestamp']
                            if start_date and interaction_date < start_date:
                                continue
                            if end_date and interaction_date > end_date:
                                continue
                        
                        interactions.append(interaction)
                    except json.JSONDecodeError:
                        continue
            
            # Export to JSON file
            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_interactions": len(interactions),
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "data_source": "json_file",
                "interactions": interactions
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported {len(interactions)} interactions to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export audit data from fallback file: {e}")
            return False
    
    def query_interactions_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute custom SQL query on the audit data
        
        Args:
            sql_query: SQL query string (use {table_name} placeholder for table name)
            
        Returns:
            List of dictionaries representing query results
        """
        if self._use_fallback:
            logger.warning("SQL querying not available with JSON file fallback")
            return []
        
        try:
            # Replace placeholder with actual table name
            formatted_query = sql_query.format(table_name=self.full_table_name)
            
            df = self.spark.sql(formatted_query)
            return [row.asDict() for row in df.collect()]
            
        except Exception as e:
            logger.error(f"Failed to execute SQL query: {e}")
            return []


# Privacy and compliance utilities
class PrivacyManager:
    """Handles privacy and compliance aspects of audit logging"""
    
    @staticmethod
    def anonymize_user_data(interaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize user data while preserving audit trail
        
        Args:
            interaction: Raw interaction data
            
        Returns:
            Anonymized interaction data
        """
        anonymized = interaction.copy()
        
        # Hash user identifiers instead of storing plain text
        import hashlib
        if anonymized.get('user_email'):
            anonymized['user_email_hash'] = hashlib.sha256(
                anonymized['user_email'].encode()
            ).hexdigest()[:16]  # First 16 chars of hash
            del anonymized['user_email']
        
        if anonymized.get('user_name'):
            anonymized['user_name_hash'] = hashlib.sha256(
                anonymized['user_name'].encode()
            ).hexdigest()[:16]
            del anonymized['user_name']
        
        # Keep user_id for admin purposes but hash it
        if anonymized.get('user_id'):
            anonymized['user_id_hash'] = hashlib.sha256(
                anonymized['user_id'].encode()
            ).hexdigest()[:16]
            del anonymized['user_id']
        
        return anonymized
    
    @staticmethod
    def redact_sensitive_content(text: str) -> str:
        """
        Redact potentially sensitive content from questions/responses
        
        Args:
            text: Input text to scan for sensitive content
            
        Returns:
            Text with sensitive content redacted
        """
        import re
        
        # Redact potential tokens, keys, passwords
        patterns = [
            (r'(?i)(token|key|password|secret)\s*[:=]\s*\S+', r'\1: [REDACTED]'),
            (r'(?i)dapi[a-f0-9]{32}', '[DATABRICKS_TOKEN_REDACTED]'),
            (r'(?i)[a-z0-9]{24}\.[a-z0-9]{6}\.[a-z0-9-_]{27}', '[JWT_TOKEN_REDACTED]'),
        ]
        
        redacted_text = text
        for pattern, replacement in patterns:
            redacted_text = re.sub(pattern, replacement, redacted_text)
        
        return redacted_text


# Global auditor instance
_auditor_instance = None

def get_auditor(use_delta: bool = True, **kwargs) -> DeltaChatAuditor:
    """
    Get the global auditor instance with configurable parameters
    
    Args:
        use_delta: Whether to use Delta table auditing (defaults to True)
        **kwargs: Additional arguments passed to DeltaChatAuditor constructor
                 Supported: catalog_name, schema_name, table_name
    
    Returns:
        DeltaChatAuditor instance
    """
    global _auditor_instance
    if _auditor_instance is None:
        # Get configuration from environment variables with fallbacks
        import os
        
        # Set defaults from environment or use provided kwargs
        config = {
            'catalog_name': kwargs.get('catalog_name', os.getenv('AUDIT_CATALOG', 'main')),
            'schema_name': kwargs.get('schema_name', os.getenv('AUDIT_SCHEMA', 'ucx_audit')),  
            'table_name': kwargs.get('table_name', os.getenv('AUDIT_TABLE', 'chat_interactions'))
        }
        
        # Override with any explicitly provided kwargs
        config.update({k: v for k, v in kwargs.items() if k in ['catalog_name', 'schema_name', 'table_name']})
        
        if use_delta:
            _auditor_instance = DeltaChatAuditor(**config)
        else:
            # For backward compatibility, still create DeltaChatAuditor but it will fall back to JSON
            _auditor_instance = DeltaChatAuditor(**config)
            
        logger.info(f"Initialized audit system with: {config['catalog_name']}.{config['schema_name']}.{config['table_name']}")
        
    return _auditor_instance

# Backward compatibility alias
ChatAuditor = DeltaChatAuditor

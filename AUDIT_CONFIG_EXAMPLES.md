# UCX Audit Configuration Examples

This document provides various configuration examples for the UCX troubleshooting app's audit system.

## Environment-Specific Configurations

### Development Environment
```yaml
# databricks.yml
targets:
  dev:
    variables:
      audit_catalog: "main"
      audit_schema: "ucx_audit_dev"
      audit_table: "chat_interactions"
```
**Result**: `main.ucx_audit_dev.chat_interactions`

### Staging Environment  
```yaml
# databricks.yml
targets:
  staging:
    variables:
      audit_catalog: "main"
      audit_schema: "ucx_audit_staging"
      audit_table: "chat_interactions"
```
**Result**: `main.ucx_audit_staging.chat_interactions`

### Production Environment
```yaml
# databricks.yml
targets:
  prod:
    variables:
      audit_catalog: "shared"
      audit_schema: "ucx_audit_prod"
      audit_table: "chat_interactions"
```
**Result**: `shared.ucx_audit_prod.chat_interactions`

## Multi-Tenant Configurations

### Per-Organization Setup
```yaml
# databricks.yml for Organization A
variables:
  audit_catalog: "org_a_catalog"
  audit_schema: "ucx_audit"

# databricks.yml for Organization B  
variables:
  audit_catalog: "org_b_catalog"
  audit_schema: "ucx_audit"
```

### Per-Team Setup
```yaml
# For Data Engineering Team
variables:
  audit_catalog: "main"
  audit_schema: "de_team_ucx_audit"

# For Analytics Team
variables:
  audit_catalog: "main"
  audit_schema: "analytics_team_ucx_audit"
```

## Compliance-Focused Configurations

### Enterprise Compliance
```yaml
# Centralized audit location
variables:
  audit_catalog: "compliance_catalog"
  audit_schema: "application_audit_logs"
  audit_table: "ucx_interactions"
```
**Result**: `compliance_catalog.application_audit_logs.ucx_interactions`

### Regional Compliance
```yaml
# For GDPR compliance (Europe)
variables:
  audit_catalog: "eu_data_catalog"
  audit_schema: "ucx_audit_eu"
  
# For US compliance
variables:
  audit_catalog: "us_data_catalog" 
  audit_schema: "ucx_audit_us"
```

## Development Workflow Examples

### Local Development Override
```bash
# Override for local testing
export AUDIT_CATALOG="dev_sandbox"
export AUDIT_SCHEMA="personal_testing"
streamlit run app.py
```

### CI/CD Pipeline Configuration
```yaml
# GitHub Actions example
env:
  AUDIT_CATALOG: ${{ secrets.AUDIT_CATALOG }}
  AUDIT_SCHEMA: "ucx_audit_${{ github.ref_name }}"  # Branch-based schema
  AUDIT_TABLE: "chat_interactions"
```

## Migration Scenarios

### Migrating from JSON to Delta
1. **Current**: JSON files in `audit_logs/`
2. **Target**: Delta table `analytics.ucx_systems.chat_audit`

```bash
# Step 1: Deploy with new configuration
export AUDIT_CATALOG="analytics"
export AUDIT_SCHEMA="ucx_systems" 
export AUDIT_TABLE="chat_audit"
databricks bundle deploy --target prod

# Step 2: Verify table creation
databricks sql "DESCRIBE TABLE analytics.ucx_systems.chat_audit"

# Step 3: Optional - Import historical JSON data
python migrate_json_to_delta.py --source audit_logs/ --target analytics.ucx_systems.chat_audit
```

## Configuration Validation

### Check Current Configuration
```python
from config_helper import AuditConfig

# Get current config
config = AuditConfig.get_config()
print(f"Table: {config['full_table_name']}")

# Validate configuration
validation = AuditConfig.validate_config()
if not validation['valid']:
    for error in validation['errors']:
        print(f"Error: {error}")
```

### Test Configuration
```bash
# Test with temporary settings
AUDIT_CATALOG="test_catalog" \
AUDIT_SCHEMA="temp_schema" \
AUDIT_TABLE="test_interactions" \
python -c "from config_helper import AuditConfig; print(AuditConfig.get_config())"
```

## Best Practices

### Naming Conventions
```yaml
# Good: Clear, consistent naming
audit_catalog: "data_governance"
audit_schema: "ucx_audit_prod"
audit_table: "chat_interactions"

# Avoid: Ambiguous or inconsistent naming  
audit_catalog: "stuff"
audit_schema: "random123"
```

### Access Control Setup
```sql
-- Grant permissions for production
GRANT CREATE SCHEMA ON CATALOG shared TO `ucx-app-service-principal`;
GRANT SELECT, INSERT ON TABLE shared.ucx_audit_prod.chat_interactions TO `audit-readers-group`;
```

### Monitoring Configuration
```sql  
-- Monitor table growth
SELECT 
  DATE(timestamp) as date,
  COUNT(*) as daily_interactions,
  approx_count_distinct(user_email) as daily_users
FROM ${audit_catalog}.${audit_schema}.${audit_table}
WHERE timestamp >= current_date() - interval 7 days
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

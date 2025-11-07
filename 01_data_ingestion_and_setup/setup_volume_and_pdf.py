# Databricks notebook source
# MAGIC %md
# MAGIC ## Automated Volume Creation and PDF Setup
# MAGIC This notebook automatically:
# MAGIC 1. Creates the Unity Catalog volume if it doesn't exist
# MAGIC 2. Copies the PDF from the repo to the volume

# COMMAND ----------

dbutils.widgets.text("catalog_name", "", "")
catalog_name = dbutils.widgets.get("catalog_name")

dbutils.widgets.text("schema_name", "", "")
schema_name = dbutils.widgets.get("schema_name")

dbutils.widgets.text("volume_name", "pdf_sources", "")
volume_name = dbutils.widgets.get("volume_name")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create Volume (if not exists)

# COMMAND ----------

# Create volume using SQL
volume_full_name = f"{catalog_name}.{schema_name}.{volume_name}"

create_volume_sql = f"""
CREATE VOLUME IF NOT EXISTS {volume_full_name}
"""

print(f"Creating volume: {volume_full_name}")
spark.sql(create_volume_sql)
print(f"✓ Volume ready: {volume_full_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Copy PDF from Repo to Volume

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Copy PDF from Repo to Volume

# COMMAND ----------

# Get the current notebook path and derive repo root
notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
repo_root = "/Workspace" + "/".join(notebook_path.split("/")[:-2])

# Source PDF in repo root
pdf_source_workspace = f"{repo_root}/ucx_errors.pdf"
pdf_destination = f"/Volumes/{catalog_name}/{schema_name}/{volume_name}/ucx_errors.pdf"

print(f"Copying PDF...")
print(f"  Workspace path: {pdf_source_workspace}")
print(f"  Destination: {pdf_destination}")

# For files in Workspace, we need to use Python file operations, not dbutils.fs.cp
import shutil

try:
    # Convert workspace path to local file path for reading
    # In Databricks, workspace files can be read directly using open()
    with open(pdf_source_workspace, 'rb') as source_file:
        pdf_content = source_file.read()
    
    # Write to Volume using Python file operations
    with open(pdf_destination, 'wb') as dest_file:
        dest_file.write(pdf_content)
    
    print("✓ PDF copied successfully!")
    
except FileNotFoundError as e:
    print(f"Error: Source PDF not found at {pdf_source_workspace}")
    print(f"Trying alternative method using dbutils.fs.head to check...")
    try:
        # Check if we can see it with dbutils.fs
        files = dbutils.fs.ls(repo_root)
        print(f"Files in {repo_root}:")
        for f in files:
            print(f"  - {f.name}")
    except Exception as e2:
        print(f"Error listing directory: {e2}")
    raise e
except Exception as e:
    print(f"Copy operation error: {e}")
    # Check if file already exists in destination
    try:
        with open(pdf_destination, 'rb') as f:
            print("✓ PDF already exists in volume")
    except:
        raise e

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verify Setup

# COMMAND ----------

# List files in volume
print(f"\nFiles in volume {volume_full_name}:")
files = dbutils.fs.ls(f"/Volumes/{catalog_name}/{schema_name}/{volume_name}/")
for f in files:
    print(f"  - {f.name} ({f.size} bytes)")

print("\n✓ Setup complete! Ready for PDF ingestion.")
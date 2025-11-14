# Databricks notebook source
# MAGIC %md
# MAGIC ## Automated Volume Creation and Document Setup
# MAGIC This notebook automatically:
# MAGIC 1. Creates the Unity Catalog volume if it doesn't exist
# MAGIC 2. Copies documents from Workspace folder to the volume

# COMMAND ----------

dbutils.widgets.text("catalog_name", "", "Catalog Name")
catalog_name = dbutils.widgets.get("catalog_name")

dbutils.widgets.text("schema_name", "", "Schema Name")
schema_name = dbutils.widgets.get("schema_name")

dbutils.widgets.text("volume_name", "document_sources", "Volume Name")
volume_name = dbutils.widgets.get("volume_name")

dbutils.widgets.text("workspace_documents_path", "", "Workspace Path with Documents")
workspace_documents_path = dbutils.widgets.get("workspace_documents_path")

dbutils.widgets.text("internal_documents_volume_path", "", "Full Volume Path (with prefix)")
internal_documents_volume_path = dbutils.widgets.get("internal_documents_volume_path")

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
# MAGIC ## 2. Copy Documents from Workspace to Volume

# COMMAND ----------

import os
import shutil

# Supported file extensions for ai_parse_document
SUPPORTED_EXTENSIONS = {
    '.pdf',           # PDF documents
    '.doc', '.docx',  # Microsoft Word
    '.ppt', '.pptx',  # Microsoft PowerPoint
    '.jpg', '.jpeg',  # JPEG images
    '.png'            # PNG images
}

def copy_documents_from_workspace(workspace_path, volume_path):
    """
    Copy supported documents from Workspace folder to Unity Catalog Volume
    """
    if not workspace_path:
        print("ℹ️  No workspace path provided.")
        print(f"📁 Please upload your documents directly to: {volume_path}")
        print("")
        print("Supported formats: PDF, DOCX, DOC, PPTX, PPT, JPG, JPEG, PNG")
        return 0
    
    print(f"Copying documents from: {workspace_path}")
    print(f"                    to: {volume_path}")
    print("")
    
    # Check if source path exists
    if not os.path.exists(workspace_path):
        print(f"✗ Error: Workspace path does not exist: {workspace_path}")
        print(f"📁 Please upload your documents directly to: {volume_path}")
        return 0
    
    copied_count = 0
    skipped_count = 0
    
    # List all files in workspace path
    try:
        for item in os.listdir(workspace_path):
            source_file = os.path.join(workspace_path, item)
            
            # Skip directories
            if os.path.isdir(source_file):
                continue
            
            # Check if file extension is supported
            file_ext = os.path.splitext(item)[1].lower()
            
            if file_ext not in SUPPORTED_EXTENSIONS:
                print(f"  ⊘ Skipping unsupported file: {item}")
                skipped_count += 1
                continue
            
            # Copy to volume
            try:
                destination_file = os.path.join(volume_path, item)
                print(f"  ↓ Copying: {item}")
                
                shutil.copy2(source_file, destination_file)
                
                file_size = os.path.getsize(destination_file)
                print(f"    ✓ Copied: {item} ({file_size:,} bytes)")
                copied_count += 1
                
            except Exception as e:
                print(f"    ✗ Error copying {item}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"✗ Error listing workspace path: {str(e)}")
        return 0
    
    print(f"\n✓ Copy complete!")
    print(f"  - Copied: {copied_count} files")
    print(f"  - Skipped: {skipped_count} files")
    
    return copied_count

# COMMAND ----------

# Copy documents from workspace to volume (with project prefix)
copied = copy_documents_from_workspace(workspace_documents_path, internal_documents_volume_path)

if copied > 0:
    print(f"\n✓ Successfully copied {copied} file(s) from Workspace to Volume")
elif not workspace_documents_path:
    print("\nℹ️  No source path provided. Upload files manually to the volume path shown above.")
else:
    print("\nℹ️  No files copied. You can upload files manually to the volume.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verify Setup

# COMMAND ----------

# List files in volume
print(f"\nFiles in {volume_full_name} ({internal_documents_volume_path}):")
try:
    files = dbutils.fs.ls(internal_documents_volume_path)
    
    if len(files) == 0:
        print("  (No files found)")
    else:
        for f in files:
            print(f"  - {f.name}")
        print(f"\nTotal: {len(files)} files")
except Exception as e:
    print(f"  (Directory not found or empty - this is normal if no files uploaded yet)")

print("\n✓ Setup complete! Ready for document ingestion.")
print(f"📁 Upload documents to: {internal_documents_volume_path}")

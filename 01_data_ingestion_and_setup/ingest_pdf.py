# Databricks notebook source
# MAGIC %md
# MAGIC ## 0. Install libraries and load widgets

# COMMAND ----------

# MAGIC %pip install pypdf2 unstructured
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("table_pdf_errors", "", "")
table_pdf_errors = dbutils.widgets.get("table_pdf_errors")

dbutils.widgets.text("pdf_volume_path", "", "")
pdf_volume_path = dbutils.widgets.get("pdf_volume_path")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ingest PDF data

# COMMAND ----------

import os
import pandas as pd
from PyPDF2 import PdfReader

def ingest_pdf_files(pdf_path, chunk_size=1000):
    """
    Ingest PDF files from Unity Catalog Volume
    """
    records = []
    chunk_id = 1
    
    # Use dbutils to work with Volumes
    if pdf_path.endswith('.pdf'):
        pdf_files = [pdf_path]
    else:
        # List all PDF files using dbutils
        file_list = dbutils.fs.ls(pdf_path)
        pdf_files = [f.path for f in file_list if f.path.endswith('.pdf')]
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file}")
        
        try:
            # For Unity Catalog Volumes, use standard Python file operations
            # Volumes support POSIX-like file access
            with open(pdf_file, 'rb') as f:
                reader = PdfReader(f)
                file_name = pdf_file.split('/')[-1]
                
                # Extract text from all pages
                full_text = ""
                for page_num, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text()
                    full_text += f"\n--- Page {page_num} ---\n{page_text}"
            
            # Split into chunks
            num_chunks = (len(full_text) + chunk_size - 1) // chunk_size
            
            for i in range(num_chunks):
                start = i * chunk_size
                end = min(start + chunk_size, len(full_text))
                chunk_content = full_text[start:end]
                
                records.append({
                    'chunk_id': f"pdf:{chunk_id:05}",
                    'file_name': file_name,
                    'file_path': pdf_file,
                    'file_url': pdf_file,
                    'chunk_index': i + 1,
                    'total_chunks': num_chunks,
                    'embed_input': chunk_content,
                    'doc_type': 'pdf_errors_resolutions',
                    'char_count': len(chunk_content)
                })
                chunk_id += 1
                
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Created {len(records)} chunks from {len(pdf_files)} PDF file(s)")
    
    if len(records) == 0:
        raise Exception("No chunks created! Please check the PDF file path and contents.")
    
    # Save to Delta
    pdf_df = pd.DataFrame(records)
    df = spark.createDataFrame(pdf_df)
    
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_pdf_errors)
    
    print(f"✓ Saved to {table_pdf_errors}")
    display(df)
    
    return f"{len(records)} chunks from {len(pdf_files)} files"

# COMMAND ----------

result = ingest_pdf_files(pdf_volume_path, chunk_size=1000)

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE IDENTIFIER(:table_pdf_errors) SET TBLPROPERTIES (delta.enableChangeDataFeed = true)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM IDENTIFIER(:table_pdf_errors)
# Databricks notebook source
# MAGIC %md
# MAGIC ## 0. Load widgets

# COMMAND ----------

dbutils.widgets.text("table_internal_documents", "", "")
table_internal_documents = dbutils.widgets.get("table_internal_documents")

dbutils.widgets.text("internal_documents_volume_path", "", "")
internal_documents_volume_path = dbutils.widgets.get("internal_documents_volume_path")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ingest Internal Documents with ai_parse_document
# MAGIC
# MAGIC Uses Databricks native AI function to parse PDF, Word, PowerPoint, and image files.
# MAGIC Requires Databricks Runtime 17.1+

# COMMAND ----------

from pyspark.sql.functions import col, expr, explode

def ingest_internal_document_files(volume_path, table_name):
    """
    Ingest internal documents from Unity Catalog Volume using ai_parse_document
    Supports: PDF, DOCX, DOC, PPTX, PPT, JPG, JPEG, PNG
    """
    
    print(f"Reading documents from: {volume_path}")
    
    # Supported file extensions for ai_parse_document
    file_pattern = f"{volume_path}/*.{{pdf,doc,docx,ppt,pptx,jpg,jpeg,png}}"
    
    # Read files as binary
    df_binary = spark.read.format("binaryFile").load(file_pattern)
    
    file_count = df_binary.count()
    print(f"Found {file_count} document(s)")
    
    if file_count == 0:
        raise Exception("No supported documents found!")
    
    # Parse documents with ai_parse_document (version 2.0)
    print("Parsing documents with ai_parse_document...")
    df_parsed = df_binary.withColumn(
        "parsed", 
        expr("ai_parse_document(content, map('version', '2.0'))")
    )
    
    # Extract elements and metadata
    df_elements = df_parsed.select(
        col("path"),
        expr("parsed:document:elements::array<variant>").alias("elements"),
        expr("parsed:error_status::array<variant>").alias("error_status"),
        expr("parsed:metadata").alias("metadata")
    )
    
    # Check for errors and display detailed error messages
    df_errors = df_elements.filter(col("error_status").isNotNull())
    error_count = df_errors.count()
    if error_count > 0:
        print(f"⚠ Warning: {error_count} document(s) had errors")
        print("\nError details:")
        df_error_details = df_errors.select(
            expr("split(path, '/')[size(split(path, '/')) - 1]").alias("file_name"),
            col("path"),
            expr("error_status[0]:error_message::string").alias("error_message"),
            expr("error_status[0]:page_id::int").alias("page_id")
        )
        df_error_details.show(truncate=False)
        
    # Show successfully parsed documents
    df_success = df_elements.filter(col("error_status").isNull())
    success_count = df_success.count()
    print(f"\n✓ Successfully parsed {success_count} document(s)")
    if success_count > 0:
        df_success.select(
            expr("split(path, '/')[size(split(path, '/')) - 1]").alias("file_name")
        ).show(truncate=False)
    
    # Explode elements into individual rows
    df_chunks = df_elements.filter(col("error_status").isNull()).withColumn(
        "element", explode("elements")
    ).select(
        col("path"),
        expr("split(path, '/')[size(split(path, '/')) - 1]").alias("file_name"),
        expr("substring_index(split(path, '/')[size(split(path, '/')) - 1], '.', -1)").alias("file_type"),
        expr("element:id::int").alias("element_id"),
        expr("element:type::string").alias("element_type"),
        expr("element:content::string").alias("content"),
        expr("element:description::string").alias("description")
    )
    
    # Filter out empty content
    df_chunks = df_chunks.filter(
        (col("content").isNotNull()) & (col("content") != "")
    )
    
    # Create final chunk structure with enriched content
    df_final = df_chunks.withColumn(
        "embed_input",
        expr("""
            CASE 
                WHEN element_type = 'figure' AND description IS NOT NULL 
                    THEN concat('[Figure] ', description)
                WHEN element_type = 'table'
                    THEN concat('[Table] ', content)
                ELSE content
            END
        """)
    ).withColumn(
        "chunk_id",
        expr("concat(regexp_replace(file_name, '[^a-zA-Z0-9]', '_'), ':', lpad(element_id, 5, '0'))")
    ).withColumn(
        "char_count",
        expr("length(embed_input)")
    ).select(
        col("chunk_id"),
        col("file_name"),
        col("path").alias("file_path"),
        col("path").alias("file_url"),
        col("file_type"),
        col("element_id").alias("chunk_index"),
        col("element_type").alias("doc_type"),
        col("embed_input"),
        col("char_count")
    ).filter(col("char_count") > 20)  # Filter out very small chunks
    
    chunk_count = df_final.count()
    print(f"Created {chunk_count} chunks from {file_count} document(s)")
    
    if chunk_count == 0:
        error_msg = """
No chunks created! All documents failed to parse.

Possible causes:
1. Documents may be corrupted or password-protected
2. File formats may not be supported (check file extensions)
3. ai_parse_document may require additional permissions or configuration
4. Documents may be empty or have no extractable content

Please check the error details above and verify:
- Files are valid and not corrupted
- Files are not password-protected
- Your Databricks Runtime version is 17.1 or higher
- You have necessary permissions to use AI functions
"""
        raise Exception(error_msg)
    
    # Save to Delta
    print(f"Saving to {table_name}...")
    df_final.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
    
    print(f"✓ Saved to {table_name}")
    display(df_final)
    
    return f"{chunk_count} chunks from {file_count} files"

# COMMAND ----------

result = ingest_internal_document_files(internal_documents_volume_path, table_internal_documents)

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE IDENTIFIER(:table_internal_documents) SET TBLPROPERTIES (delta.enableChangeDataFeed = true)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM IDENTIFIER(:table_internal_documents)


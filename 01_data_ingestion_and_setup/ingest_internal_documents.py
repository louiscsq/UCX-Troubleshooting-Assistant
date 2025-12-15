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
    """Ingest internal documents from Unity Catalog Volume using ai_parse_document.
    Supports: PDF, DOCX, DOC, PPTX, PPT, JPG, JPEG, PNG"""
    
    file_pattern = f"{volume_path}/*.{{pdf,doc,docx,ppt,pptx,jpg,jpeg,png}}"
    df_binary = spark.read.format("binaryFile").load(file_pattern)
    file_count = df_binary.count()
    
    if file_count == 0:
        raise Exception("No supported documents found!")
    
    print(f"Parsing {file_count} document(s)...")
    
    df_parsed = df_binary.withColumn("parsed", expr("ai_parse_document(content, map('version', '2.0'))"))
    
    df_elements = df_parsed.select(
        col("path"),
        expr("parsed:document:elements::array<variant>").alias("elements"),
        expr("parsed:error_status::array<variant>").alias("error_status")
    )
    
    error_count = df_elements.filter(col("error_status").isNotNull()).count()
    if error_count > 0:
        print(f"Warning: {error_count} document(s) had errors")
    
    df_elements_exploded = df_elements.filter(col("error_status").isNull()).withColumn(
        "element", explode("elements")
    ).select(
        col("path"),
        expr("split(path, '/')[size(split(path, '/')) - 1]").alias("file_name"),
        expr("substring_index(split(path, '/')[size(split(path, '/')) - 1], '.', -1)").alias("file_type"),
        expr("element:id::int").alias("element_id"),
        expr("element:type::string").alias("element_type"),
        expr("element:content::string").alias("content"),
        expr("element:description::string").alias("description")
    ).filter((col("content").isNotNull()) & (col("content") != ""))
    
    df_with_content = df_elements_exploded.withColumn(
        "enriched_content",
        expr("""
            CASE 
                WHEN element_type = 'figure' AND description IS NOT NULL THEN concat('[Figure] ', description)
                WHEN element_type = 'table' THEN concat('[Table] ', content)
                ELSE content
            END
        """)
    ).withColumn("char_count", expr("length(enriched_content)"))
    
    df_with_content.createOrReplaceTempView("elements_temp")
    
    df_chunks = spark.sql("""
        WITH running_totals AS (
            SELECT 
                *,
                SUM(char_count) OVER (PARTITION BY path ORDER BY element_id 
                                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as running_char_count
            FROM elements_temp
        ),
        chunk_groups AS (
            SELECT *, FLOOR(running_char_count / 800) as chunk_group
            FROM running_totals
        )
        SELECT 
            path, file_name, file_type, chunk_group,
            CONCAT_WS('\\n\\n', COLLECT_LIST(enriched_content)) as combined_content,
            COLLECT_LIST(element_type) as element_types
        FROM chunk_groups
        GROUP BY path, file_name, file_type, chunk_group
    """)
    
    df_final = df_chunks.withColumn(
        "chunk_id",
        expr("concat(regexp_replace(file_name, '[^a-zA-Z0-9]', '_'), ':', lpad(chunk_group, 5, '0'))")
    ).withColumn(
        "char_count", expr("length(combined_content)")
    ).withColumn(
        "doc_type", expr("CASE WHEN array_contains(element_types, 'table') THEN 'table' ELSE 'text' END")
    ).select(
        col("chunk_id"), col("file_name"),
        col("path").alias("file_path"), col("path").alias("file_url"),
        col("file_type"), col("chunk_group").alias("chunk_index"),
        col("doc_type"), col("combined_content").alias("embed_input"), col("char_count")
    ).filter(col("char_count") > 100)
    
    chunk_count = df_final.count()
    if chunk_count == 0:
        raise Exception("No chunks created. Check documents are valid and not password-protected.")
    
    print(f"Created {chunk_count} chunks from {file_count} file(s)")
    df_final.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
    
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


# Databricks notebook source
# MAGIC %md
# MAGIC ## 0. Import Libraries

# COMMAND ----------

# MAGIC %pip install sourcegraph streamlit PyYAML
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import yaml
from sourcegraph import Sourcegraph

# COMMAND ----------

dbutils.widgets.text("repo", "", "")
repo = dbutils.widgets.get("repo")
repo_url = f"https://github.com/{repo}"

dbutils.widgets.text("summarising_endpoint", "", "")
summarising_endpoint = dbutils.widgets.get("summarising_endpoint")

dbutils.widgets.text("table_codebase", "", "")
table_codebase = dbutils.widgets.get("table_codebase")

dbutils.widgets.text("github_token", "", "")
github_token = dbutils.widgets.get("github_token")

dbutils.widgets.text("config_file", "configs/ucx.config.yaml", "")
config_file = dbutils.widgets.get("config_file")

# Load the main configuration file
config_path = f"../webapp/{config_file}"
with open(config_path, "r") as f:
    main_config = yaml.safe_load(f)

summarization_prompt = main_config.get("codebase_ingestion", {}).get("summarization_prompt", "")

# Set summarization_prompt as a widget so it can be used in SQL magic cells
dbutils.widgets.text("summarization_prompt", summarization_prompt, "")
summarization_prompt = dbutils.widgets.get("summarization_prompt")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1.1. Download Python code from GitHub

# COMMAND ----------

gihub_repository = Sourcegraph(repo_url)
gihub_repository.run()
data = dict(gihub_repository.node_data)
for key, value in data.items():
  data[key]['uses'] = ", ".join(list(gihub_repository.get_dependencies(key)))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1.2. Download SQL code from GitHub

# COMMAND ----------

import requests
import pandas as pd

def get_sql_files_from_github(repo, token=None):
    api_base = "https://api.github.com/repos/" + repo
    sql_contents = []
    
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    def fetch_contents(path=""):
        url = f"{api_base}/contents/{path}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text[:200]}")
            return
            
        items = response.json()
        
        if isinstance(items, dict):
            items = [items]
        c = 1
        for item in items:
            if 'type' not in item:
                continue
                
            if item['type'] == 'file' and item['name'].endswith('.sql'):
                file_resp = requests.get(item['download_url'], headers=headers)
                sql_contents.append({
                    'chunk_id': f"sql:{str(c).zfill(3)}",
                    'file_name': item['name'],
                    'file_path': item['path'],
                    'definition': file_resp.text
                })
            elif item['type'] == 'dir':
                fetch_contents(item['path'])
            c += 1
    
    fetch_contents()
    return sql_contents

sql_data = get_sql_files_from_github(repo, token=github_token)
print(f"Found {len(sql_data)} SQL files")

if sql_data:
    df_sql = pd.DataFrame(sql_data)
    sql_df = spark.createDataFrame(df_sql)
    display(sql_df)
else:
    print("No SQL files found in repository")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Combine datasets, then save to delta

# COMMAND ----------

import pandas as pd
records = []
embed_inputs = []

for i, code_metadata in enumerate(data.values(), start=1):
    record = code_metadata.copy()
    record['chunk_id'] = f"code:{i:03}"
    records.append(record)

pdf = pd.DataFrame(records)
python_df = spark.createDataFrame(pdf)
display(python_df)

# COMMAND ----------

combined_df = sql_df.select("chunk_id", "file_name", "definition").union(python_df.select("chunk_id", "file_name", "definition"))

# COMMAND ----------

delta_path = table_codebase
combined_df.write.format("delta").option("overwriteSchema", "true").mode("overwrite").saveAsTable(delta_path)    
print(f"{combined_df.count()} documents indexed")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM IDENTIFIER(:table_codebase)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate embedding input for Vector Search

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE IDENTIFIER(:table_codebase) AS 
# MAGIC SELECT *, CONCAT(
# MAGIC   definition, '\n\n', ai_query(
# MAGIC      :summarising_endpoint, 
# MAGIC     CONCAT(
# MAGIC       :summarization_prompt, 
# MAGIC       definition
# MAGIC     )
# MAGIC   )
# MAGIC ) AS embed_input 
# MAGIC FROM IDENTIFIER(:table_codebase)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Add URL reference for Vector Search documents

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE IDENTIFIER(:table_codebase) AS 
# MAGIC SELECT *, CONCAT("https://github.com/search?q=repo:", :repo ,"+path:/", file_name, "&type=code") AS file_url FROM IDENTIFIER(:table_codebase)
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE IDENTIFIER(:table_codebase) SET TBLPROPERTIES (delta.enableChangeDataFeed = true)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM IDENTIFIER(:table_codebase) where file_name like "%sql%"
# Databricks notebook source
# MAGIC %pip install -U -qqqq backoff databricks-openai uv databricks-agents>=1.2.0 mlflow>=3.1.0 databricks-vectorsearch==0.55

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
import time


def get_widget(name: str, default: str = "", label: str = "") -> str:
  dbutils.widgets.text(name, default, label)
  return dbutils.widgets.get(name)


def index_exists(vsc, endpoint_name, index_full_name):
    try:
        dict_vsindex = vsc.get_index(endpoint_name, index_full_name).describe()
        return dict_vsindex.get('status').get('ready', False)
    except Exception as e:
        if 'RESOURCE_DOES_NOT_EXIST' not in str(e):
            print(f'Unexpected error describing the index. This could be a permission issue.')
            raise e
    return False


def endpoint_exists(vsc, vs_endpoint_name):
  try:
    return vs_endpoint_name in [e['name'] for e in vsc.list_endpoints().get('endpoints', [])]
  except Exception as e:
    #Temp fix for potential REQUEST_LIMIT_EXCEEDED issue
    if "REQUEST_LIMIT_EXCEEDED" in str(e):
      print("WARN: couldn't get endpoint status due to REQUEST_LIMIT_EXCEEDED error. The demo will consider it exists")
      return True
    else:
      raise e

def wait_for_index_to_be_ready(vsc, vs_endpoint_name, index_name):
  for i in range(180):
    idx = vsc.get_index(vs_endpoint_name, index_name).describe()
    index_status = idx.get('status', idx.get('index_status', {}))
    status = index_status.get('detailed_state', index_status.get('status', 'UNKNOWN')).upper()
    url = index_status.get('index_url', index_status.get('url', 'UNKNOWN'))
    if "ONLINE" in status:
      return
    if "UNKNOWN" in status:
      print(f"Can't get the status - will assume index is ready {idx} - url: {url}")
      return
    elif "PROVISIONING" in status:
      if i % 40 == 0: print(f"Waiting for index to be ready, this can take a few min... {index_status} - pipeline url:{url}")
      time.sleep(10)
    else:
        raise Exception(f'''Error with the index - this shouldn't happen. DLT pipeline might have been killed.\n Please delete it and re-run the previous cell: vsc.delete_index("{index_name}, {vs_endpoint_name}") \nIndex details: {idx}''')
  raise Exception(f"Timeout, your index isn't ready yet: {vsc.get_index(index_name, vs_endpoint_name)}")



# New: wait for Vector Search endpoint to be ONLINE before index ops
def wait_for_vs_endpoint_to_be_ready(vsc, vs_endpoint_name):
  for i in range(180):
    try:
      endpoint = vsc.get_endpoint(vs_endpoint_name)
    except Exception as e:
      #Temp fix for potential REQUEST_LIMIT_EXCEEDED issue
      if "REQUEST_LIMIT_EXCEEDED" in str(e):
        print("WARN: couldn't get endpoint status due to REQUEST_LIMIT_EXCEEDED error. Please manually check your endpoint status")
        return
      else:
        raise e
    status = endpoint.get("endpoint_status", endpoint.get("status"))["state"].upper()
    if "ONLINE" in status:
      return endpoint
    elif "PROVISIONING" in status or i <6:
      if i % 20 == 0: 
        print(f"Waiting for endpoint to be ready, this can take a few min... {endpoint}")
      time.sleep(10)
    else:
      raise Exception(f'''Error with the endpoint {vs_endpoint_name}. - this shouldn't happen: {endpoint}.\n Please delete it and re-run the previous cell: vsc.delete_endpoint("{vs_endpoint_name}")''')
  raise Exception(f"Timeout, your endpoint isn't ready yet: {vsc.get_endpoint(vs_endpoint_name)}")

# COMMAND ----------

vector_search_endpoint = get_widget("vector_search_endpoint", "", "")
table_source = get_widget("table_source", "", "")
embedding_model_endpoint = "databricks-gte-large-en"

# COMMAND ----------

if not table_source:
  raise ValueError("Parameter 'table_source' is required")

if not vector_search_endpoint:
  raise ValueError("Parameter 'vector_search_endpoint' is required")

index_name = f"{table_source}_vector"

from databricks.vector_search.client import VectorSearchClient
vsc = VectorSearchClient()

if not endpoint_exists(vsc, vector_search_endpoint):
    vsc.create_endpoint(name=vector_search_endpoint, endpoint_type="STANDARD")

wait_for_vs_endpoint_to_be_ready(vsc, vector_search_endpoint)
print(f"Endpoint named {vector_search_endpoint} is ready.")

# COMMAND ----------

vs_index_fullname = index_name
source_table_fullname = table_source

wait_for_vs_endpoint_to_be_ready(vsc, vector_search_endpoint)

# Check if the source table has a doc_type or type column
table_columns = [field.name for field in spark.table(source_table_fullname).schema.fields]
columns_to_sync = ["chunk_id", "embed_input", "file_url"]

# Add doc_type or type column if it exists in the source table
if "doc_type" in table_columns:
    columns_to_sync.append("doc_type")
elif "type" in table_columns:
    columns_to_sync.append("type")

print(f"Columns to sync: {columns_to_sync}")

if not index_exists(vsc, vector_search_endpoint, vs_index_fullname):
  print(f"Creating index {vs_index_fullname} on endpoint {vector_search_endpoint}...")
  try:
    vsc.create_delta_sync_index(
      endpoint_name=vector_search_endpoint,
      source_table_name=source_table_fullname,
      index_name=vs_index_fullname,
      primary_key="chunk_id",
      columns_to_sync=columns_to_sync,
      pipeline_type="TRIGGERED",
      embedding_source_column="embed_input",
      embedding_model_endpoint_name=embedding_model_endpoint,
    )
  except Exception as e:
    print(f"Error creating index on endpoint '{vector_search_endpoint}': {e}")
    raise

  # Wait for the index to be ready
  wait_for_index_to_be_ready(vsc, vector_search_endpoint, vs_index_fullname)
else:
  # Ensure current index is healthy, then trigger a sync to pick up latest table changes
  wait_for_index_to_be_ready(vsc, vector_search_endpoint, vs_index_fullname)
  vsc.get_index(vector_search_endpoint, vs_index_fullname).sync()

print(f"✓ Vector Search index ready: {vs_index_fullname}")
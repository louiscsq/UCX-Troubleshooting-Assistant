# Databricks notebook source
# MAGIC %md
# MAGIC ## 0. Load Libraries and widgets

# COMMAND ----------

dbutils.widgets.text("repo", "", "")
repo = dbutils.widgets.get("repo")
repo_url = f"https://github.com/{repo}"
print(f"Repo URL: {repo_url}")

dbutils.widgets.text("table_documentation", "", "")
table_documentation = dbutils.widgets.get("table_documentation")

dbutils.widgets.text("github_token", "", "")
github_token = dbutils.widgets.get("github_token")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ingest readme data

# COMMAND ----------

def ingest_readme_data_simple(repo_url, chunk_size=1500, github_token=None):
    import requests
    import base64
    import re
    import pandas as pd
    import time
    
    headers = {}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    pattern = r'github\.com/([^/]+)/([^/]+?)(?:\.git)?$'
    match = re.search(pattern, repo_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    owner, repo = match.groups()
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    
    print("Fetching files...")
    readme_files = []
    
    # Get root README
    for readme_name in ['README.md', 'README.rst', 'README.txt']:
        try:
            response = requests.get(f"{api_base}/contents/{readme_name}", headers=headers, timeout=10)
            if response.status_code == 200:
                content = base64.b64decode(response.json()['content']).decode('utf-8')
                readme_files.append({'file_path': readme_name, 'content': content, 'type': 'readme'})
                print(f"  Found: {readme_name}")
                break
        except:
            continue
    
    # Recursive fetch with limit
    def fetch_docs(path, limit=30):
        if len(readme_files) >= limit:
            return
        try:
            response = requests.get(f"{api_base}/contents/{path}", headers=headers, timeout=10)
            if response.status_code != 200:
                return
            time.sleep(0.3)
            
            for item in response.json():
                if len(readme_files) >= limit:
                    break
                if item['type'] == 'dir':
                    fetch_docs(item['path'], limit)
                elif item['type'] == 'file' and item['name'].endswith(('.md', '.mdx')):
                    try:
                        r = requests.get(item['url'], headers=headers, timeout=10)
                        if r.status_code == 200:
                            content = base64.b64decode(r.json()['content']).decode('utf-8')
                            if len(content) > 100:
                                readme_files.append({'file_path': item['path'], 'content': content, 'type': 'documentation'})
                                print(f"  Found: {item['path']}")
                        time.sleep(0.2)
                    except:
                        pass
        except:
            pass
    
    fetch_docs('/')
    
    print(f"\nProcessing {len(readme_files)} files...")
    
    records = []
    chunk_id = 1
    
    for doc in readme_files:
        text = doc['content']
        file_path = doc['file_path']
        
        num_chunks = (len(text) + chunk_size - 1) // chunk_size
        
        for i in range(num_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(text))
            chunk_content = text[start:end]
            
            records.append({
                'chunk_id': f"chunk:{chunk_id:05}",
                'file_name': file_path.split('/')[-1],
                'file_url': repo_url + '/tree/main/' + file_path,
                'chunk_index': i + 1,
                'total_chunks': num_chunks,
                'embed_input': chunk_content,
                'doc_type': doc['type'],
                'char_count': len(chunk_content)
            })
            chunk_id += 1
    
    print(f"Created {len(records)} chunks")
    
    # Save to Delta
    pdf = pd.DataFrame(records)
    df = spark.createDataFrame(pdf)
    
    table_name = table_documentation
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)
    
    print(f"✓ Saved to {table_name}")
    display(df)
    
    return f"{len(records)} chunks from {len(readme_files)} files"

# COMMAND ----------

result = ingest_readme_data_simple(
    repo_url=repo_url, 
    github_token=github_token
)

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE IDENTIFIER(:table_documentation) SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Agent Framework: Author and deploy an OpenAI Responses API agent using a model hosted on Mosaic AI Foundation Model API

# COMMAND ----------

# MAGIC %pip install -U -qqqq backoff databricks-openai uv databricks-agents mlflow-skinny[databricks] PyYAML
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import os
import json
import yaml

dbutils.widgets.text("uc_agent_model", "", "")
uc_agent_model = dbutils.widgets.get("uc_agent_model")

dbutils.widgets.text("table_documentation", "", "")
table_documentation = dbutils.widgets.get("table_documentation")

dbutils.widgets.text("table_codebase", "", "")
table_codebase = dbutils.widgets.get("table_codebase")

dbutils.widgets.text("config_file", "configs/ucx.config.yaml", "")
config_file = dbutils.widgets.get("config_file")

# Load the main configuration file
config_path = f"../webapp/{config_file}"
with open(config_path, "r") as f:
    main_config = yaml.safe_load(f)

# Write agent configuration (system prompt, tool descriptions, LLM endpoint, vector search indexes)
# This works in serverless clusters where environment variables don't persist
agent_config = {
    "llm_endpoint": main_config.get("agent", {}).get("llm_endpoint", "databricks-claude-sonnet-4-5"),
    "system_prompt": main_config.get("agent", {}).get("system_prompt", ""),
    "tools": main_config.get("agent", {}).get("tools", {}),
    "vector_search": {}
}

# Add vector search indexes if provided
if table_documentation:
    agent_config["vector_search"]["documentation_index"] = f"{table_documentation}_vector"
if table_codebase:
    agent_config["vector_search"]["codebase_index"] = f"{table_codebase}_vector"

with open("agent_config.json", "w") as f:
    json.dump(agent_config, f)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test the agent
# MAGIC
# MAGIC Interact with the agent to test its output. Since we manually traced methods within `ResponsesAgent`, you can view the trace for each step the agent takes, with any LLM calls made via the OpenAI SDK automatically traced by autologging.
# MAGIC
# MAGIC Replace this placeholder input with an appropriate domain-specific example for your agent.

# COMMAND ----------

from agent import AGENT

result = AGENT.predict({"input": [{"role": "user", "content": "Can i migrate tables from external to managed"}]})
print(result.model_dump(exclude_none=True))

# COMMAND ----------

for chunk in AGENT.predict_stream(
    {"input": [{"role": "user", "content": "What is 6*7 in Python?"}]}
):
    print(chunk.model_dump(exclude_none=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log the agent as an MLflow model
# MAGIC
# MAGIC Log the agent as code from the `agent.py` file. See [MLflow - Models from Code](https://mlflow.org/docs/latest/models.html#models-from-code).
# MAGIC
# MAGIC ### Enable automatic authentication for Databricks resources
# MAGIC For the most common Databricks resource types, Databricks supports and recommends declaring resource dependencies for the agent upfront during logging. This enables automatic authentication passthrough when you deploy the agent. With automatic authentication passthrough, Databricks automatically provisions, rotates, and manages short-lived credentials to securely access these resource dependencies from within the agent endpoint.
# MAGIC
# MAGIC To enable automatic authentication, specify the dependent Databricks resources when calling `mlflow.pyfunc.log_model().`
# MAGIC
# MAGIC   - **TODO**: If your Unity Catalog tool queries a [vector search index](docs link) or leverages [external functions](docs link), you need to include the dependent vector search index and UC connection objects, respectively, as resources. See docs ([AWS](https://docs.databricks.com/generative-ai/agent-framework/log-agent.html#specify-resources-for-automatic-authentication-passthrough) | [Azure](https://learn.microsoft.com/azure/databricks/generative-ai/agent-framework/log-agent#resources)).
# MAGIC
# MAGIC

# COMMAND ----------

# Determine Databricks resources to specify for automatic auth passthrough at deployment time
from agent import UC_TOOL_NAMES, VECTOR_SEARCH_TOOLS
import mlflow
from mlflow.models.resources import DatabricksFunction
from pkg_resources import get_distribution

resources = []
for tool in VECTOR_SEARCH_TOOLS:
    resources.extend(tool.resources)
for tool_name in UC_TOOL_NAMES:
    resources.append(DatabricksFunction(function_name=tool_name))

with mlflow.start_run():
    # Log agent configuration as artifact
    artifacts_dict = {}
    if os.path.exists("agent_config.json"):
        artifacts_dict["agent_config.json"] = "agent_config.json"
    
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",
        pip_requirements=[
            "databricks-openai",
            "backoff",
            f"databricks-connect=={get_distribution('databricks-connect').version}",
        ],
        resources=resources,
        artifacts=artifacts_dict if artifacts_dict else None,
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate the agent with Agent Evaluation
# MAGIC
# MAGIC Use Mosaic AI Agent Evaluation to evalaute the agent's responses based on expected responses and other evaluation criteria. Use the evaluation criteria you specify to guide iterations, using MLflow to track the computed quality metrics.
# MAGIC See Databricks documentation ([AWS]((https://docs.databricks.com/aws/generative-ai/agent-evaluation) | [Azure](https://learn.microsoft.com/azure/databricks/generative-ai/agent-evaluation/)).
# MAGIC
# MAGIC
# MAGIC To evaluate your tool calls, add custom metrics. See Databricks documentation ([AWS](https://docs.databricks.com/en/generative-ai/agent-evaluation/custom-metrics.html#evaluating-tool-calls) | [Azure](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-evaluation/custom-metrics#evaluating-tool-calls)).

# COMMAND ----------

import mlflow
from mlflow.genai.scorers import RelevanceToQuery, RetrievalGroundedness, RetrievalRelevance, Safety

# Load eval dataset from config
eval_dataset = main_config.get("evaluation", {}).get("dataset", [])

eval_results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=lambda input: AGENT.predict({"input": input}),
    scorers=[RelevanceToQuery(), Safety()],  # add more scorers here if they're applicable
)

# Review the evaluation results in the MLfLow UI (see console output)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pre-deployment agent validation
# MAGIC Before registering and deploying the agent, perform pre-deployment checks using the [mlflow.models.predict()](https://mlflow.org/docs/latest/python_api/mlflow.models.html#mlflow.models.predict) API. See Databricks documentation ([AWS](https://docs.databricks.com/en/machine-learning/model-serving/model-serving-debug.html#validate-inputs) | [Azure](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/model-serving/model-serving-debug#before-model-deployment-validation-checks)).

# COMMAND ----------

mlflow.models.predict(
    model_uri=f"runs:/{logged_agent_info.run_id}/agent",
    input_data={"input": [{"role": "user", "content": "Hello!"}]},
    env_manager="uv",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register the model to Unity Catalog
# MAGIC
# MAGIC Before you deploy the agent, you must register the agent to Unity Catalog.
# MAGIC
# MAGIC - **TODO** Update the `catalog`, `schema`, and `model_name` below to register the MLflow model to Unity Catalog.

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")

# TODO: define the catalog, schema, and model name for your UC model
UC_MODEL_NAME = uc_agent_model

# register the model to UC
uc_registered_model_info = mlflow.register_model(model_uri=logged_agent_info.model_uri, name=UC_MODEL_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy the agent

# COMMAND ----------

from mlflow import MlflowClient
from databricks.agents import get_deployments, delete_deployment
from databricks import agents

client = MlflowClient()
client.set_registered_model_alias(UC_MODEL_NAME, "Champion",uc_registered_model_info.version)

registered_model_version = client.get_model_version_by_alias(UC_MODEL_NAME, "Champion")

deployments = get_deployments(model_name=UC_MODEL_NAME)

latest_version = registered_model_version.version

for deployment in deployments:
    if deployment.model_name == UC_MODEL_NAME:
        print(f"Deleting deployment: model={deployment.model_name}, version={deployment.model_version}")
        try:
            delete_deployment(model_name=deployment.model_name, model_version=deployment.model_version)
            print(f"Successfully deleted deployment for version {deployment.model_version}")
        except ValueError as e:
            print(f"Skipping deletion for version {deployment.model_version}: {str(e)}")


deployment_info = agents.deploy(
    model_name=UC_MODEL_NAME,
    model_version=registered_model_version.version,
)
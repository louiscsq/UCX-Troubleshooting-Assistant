import json
import os
import warnings
from pathlib import Path
from typing import Any, Callable, Generator, Optional
from uuid import uuid4

import backoff
import mlflow
import openai
from databricks.sdk import WorkspaceClient
from databricks_openai import UCFunctionToolkit, VectorSearchRetrieverTool
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)
from openai import OpenAI
from pydantic import BaseModel
from unitycatalog.ai.core.base import get_uc_function_client

############################################
# Load agent configuration
############################################

def load_agent_config():
    """Load agent configuration (system prompt, LLM endpoint, tool descriptions, vector search) from file or use defaults."""
    default_config = {
        "llm_endpoint": "databricks-claude-sonnet-4-5",
        "system_prompt": """You are a troubleshooting assistant with access to a codebase and documentation. 
Help users understand the codebase, diagnose issues, and find solutions.""",
        "tools": {
            "docs_retriever": {
                "name": "docs_retriever",
                "description": "Retrieves documentation including user guides and feature explanations.",
                "num_results": 10
            },
            "codebase_retriever": {
                "name": "codebase_retriever",
                "description": "Retrieves source code including function definitions, classes, and implementation details.",
                "num_results": 8
            }
        },
        "vector_search": {
            "documentation_index": "main.default.assistant_documentation_vector",
            "codebase_index": "main.default.assistant_codebase_vector"
        }
    }
    
    # Check multiple locations for the config file:
    # 1. Current directory (for local development/testing)
    # 2. artifacts/ subdirectory (where MLflow places logged artifacts relative to agent.py)
    # 3. /model/artifacts/ (absolute path in model serving environment)
    possible_paths = [
        Path("agent_config.json"),
        Path("artifacts/agent_config.json"),
        Path("/model/artifacts/agent_config.json"),
    ]
    
    for config_file in possible_paths:
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    print(f"Loaded agent config from: {config_file}")
                    return {
                        "llm_endpoint": config.get("llm_endpoint", default_config["llm_endpoint"]),
                        "system_prompt": config.get("system_prompt", default_config["system_prompt"]),
                        "tools": config.get("tools", default_config["tools"]),
                        "vector_search": config.get("vector_search", default_config["vector_search"])
                    }
            except Exception as e:
                print(f"Warning: Failed to load agent config from {config_file}: {e}")
                continue
    
    print(f"No agent config file found in any expected location. Using defaults.")
    return default_config

agent_config = load_agent_config()
LLM_ENDPOINT_NAME = agent_config["llm_endpoint"]
SYSTEM_PROMPT = agent_config["system_prompt"]
TOOL_CONFIG = agent_config["tools"]
VECTOR_SEARCH_CONFIG = agent_config["vector_search"]

class ToolInfo(BaseModel):
    """
    Class representing a tool for the agent.
    - "name" (str): The name of the tool.
    - "spec" (dict): JSON description of the tool (matches OpenAI Responses format)
    - "exec_fn" (Callable): Function that implements the tool logic
    """

    name: str
    spec: dict
    exec_fn: Callable


def create_tool_info(tool_spec, exec_fn_param: Optional[Callable] = None):
    """
    Factory function to create ToolInfo objects from a given tool spec
    and (optionally) a custom execution function.
    """
    # Remove 'strict' property, as Claude models do not support it in tool specs.
    tool_spec["function"].pop("strict", None)
    tool_name = tool_spec["function"]["name"]
    # Converts tool name with double underscores to UDF dot notation.
    udf_name = tool_name.replace("__", ".")

    # Define a wrapper that accepts kwargs for the UC tool call,
    # then passes them to the UC tool execution client
    def exec_fn(**kwargs):
        function_result = uc_function_client.execute_function(udf_name, kwargs)
        # Return error message if execution fails, result value if not.
        if function_result.error is not None:
            return function_result.error
        else:
            return function_result.value

    return ToolInfo(name=tool_name, spec=tool_spec, exec_fn=exec_fn_param or exec_fn)


# List to store information about all tools available to the agent.
TOOL_INFOS = []

# UDFs in Unity Catalog can be exposed as agent tools.
# The following code enables a python code interpreter tool using the system.ai.python_exec UDF.

# TODO: Add additional tools
UC_TOOL_NAMES = []

uc_function_client = get_uc_function_client()
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)
for tool_spec in uc_toolkit.tools:
    TOOL_INFOS.append(create_tool_info(tool_spec))


# Use Databricks vector search indexes as tools
# See https://docs.databricks.com/en/generative-ai/agent-framework/unstructured-retrieval-tools.html#locally-develop-vector-search-retriever-tools-with-ai-bridge
# List to store vector search tool instances for unstructured retrieval.
VECTOR_SEARCH_TOOLS = []

# Vector search indexes are now loaded from the agent config
DOCUMENTATION_INDEX = VECTOR_SEARCH_CONFIG.get("documentation_index", "main.default.assistant_documentation_vector")
CODEBASE_INDEX = VECTOR_SEARCH_CONFIG.get("codebase_index", "main.default.assistant_codebase_vector")
INTERNAL_DOCUMENTS_INDEX = VECTOR_SEARCH_CONFIG.get("internal_documents_index", None)

docs_tool_config = TOOL_CONFIG.get("docs_retriever", {})
VECTOR_SEARCH_TOOLS.append(
  VectorSearchRetrieverTool(
    index_name=DOCUMENTATION_INDEX,
    tool_name=docs_tool_config.get("name", "docs_retriever"),
    doc_uri="file_url",
    tool_description=docs_tool_config.get("description", "Retrieves documentation"),
    num_results=docs_tool_config.get("num_results", 10),
    dynamic_filter=False,  # Disable filter parameters - prevents LLM from passing type/doc_type filters
    filters=None,  # No predefined filters
    columns=["chunk_id", "embed_input", "file_url"]  # Only return these columns
  )
)

codebase_tool_config = TOOL_CONFIG.get("codebase_retriever", {})
VECTOR_SEARCH_TOOLS.append(
  VectorSearchRetrieverTool(
    index_name=CODEBASE_INDEX,
    tool_name=codebase_tool_config.get("name", "codebase_retriever"),
    doc_uri="file_url",
    tool_description=codebase_tool_config.get("description", "Retrieves source code"),
    num_results=codebase_tool_config.get("num_results", 8),
    dynamic_filter=False,  # Disable filter parameters - prevents LLM from passing filters
    filters=None,  # No predefined filters
    columns=["chunk_id", "embed_input", "file_url"]  # Only return these columns
  )
)

# Add internal documents retriever if index is configured
if INTERNAL_DOCUMENTS_INDEX:
    internal_docs_tool_config = TOOL_CONFIG.get("internal_docs_retriever", {})
    VECTOR_SEARCH_TOOLS.append(
      VectorSearchRetrieverTool(
        index_name=INTERNAL_DOCUMENTS_INDEX,
        tool_name=internal_docs_tool_config.get("name", "internal_docs_retriever"),
        doc_uri="file_url",
        tool_description=internal_docs_tool_config.get("description", "Retrieves internal troubleshooting documents"),
        num_results=internal_docs_tool_config.get("num_results", 10),
        dynamic_filter=False,  # Disable filter parameters - prevents LLM from passing filters
        filters=None,  # No predefined filters
        columns=["chunk_id", "embed_input", "file_url"]  # Only return these columns
      )
    )

for vs_tool in VECTOR_SEARCH_TOOLS:
    # Workaround: Manually remove 'filters' parameter from tool spec to prevent LLM from passing it
    tool_spec = vs_tool.tool
    if 'function' in tool_spec and 'parameters' in tool_spec['function']:
        properties = tool_spec['function']['parameters'].get('properties', {})
        if 'filters' in properties:
            print(f"Removing 'filters' parameter from {vs_tool.tool_name} tool spec")
            del properties['filters']
            # Also remove from required list if present
            required = tool_spec['function']['parameters'].get('required', [])
            if 'filters' in required:
                required.remove('filters')
    
    TOOL_INFOS.append(create_tool_info(tool_spec, vs_tool.execute))


# Enable MLflow tracing BEFORE instantiating the agent
# This must be called before creating the agent instance for tracing to work properly
mlflow.tracing.enable()
mlflow.openai.autolog()


class ToolCallingAgent(ResponsesAgent):
    """
    Class representing a tool-calling Agent.
    Handles both tool execution via exec_fn and LLM interactions via model serving.
    """

    def __init__(self, llm_endpoint: str, tools: list[ToolInfo]):
        """Initializes the ToolCallingAgent with tools."""
        self.llm_endpoint = llm_endpoint
        self.workspace_client = WorkspaceClient()
        self.model_serving_client: OpenAI = (
            self.workspace_client.serving_endpoints.get_open_ai_client()
        )
        self._tools_dict = {tool.name: tool for tool in tools}

    def get_tool_specs(self) -> list[dict]:
        """Returns tool specifications in the format OpenAI expects."""
        return [tool_info.spec for tool_info in self._tools_dict.values()]

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        """Executes the specified tool with the given arguments."""
        return self._tools_dict[tool_name].exec_fn(**args)

    @backoff.on_exception(backoff.expo, openai.RateLimitError)
    @mlflow.trace(span_type=SpanType.LLM)
    def call_llm(self, messages: list[dict[str, Any]]) -> Generator[dict[str, Any], None, None]:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="PydanticSerializationUnexpectedValue")
            for chunk in self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=self.prep_msgs_for_cc_llm(messages),
                tools=self.get_tool_specs(),
                stream=True,
                temperature=0.005,
            ):
                yield chunk.to_dict()

    def handle_tool_call(
        self, tool_call: dict[str, Any], messages: list[dict[str, Any]]
    ) -> ResponsesAgentStreamEvent:
        """
        Execute tool calls, add them to the running message history, and return a ResponsesStreamEvent w/ tool output
        
        Workaround for MLflow bug: When multiple parallel tool calls occur, MLflow concatenates
        their arguments into a single string. This method parses all JSON objects and executes
        the tool multiple times, combining the results.
        """
        args_str = tool_call["arguments"]
        all_args = []
        
        # Parse all JSON objects from the (possibly concatenated) arguments string
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(args_str):
            args_str_trimmed = args_str[idx:].lstrip()
            if not args_str_trimmed:
                break
            try:
                args, end_idx = decoder.raw_decode(args_str_trimmed)
                all_args.append(args)
                idx += len(args_str[idx:]) - len(args_str_trimmed) + end_idx
            except json.JSONDecodeError:
                break
        
        # If we didn't parse any valid JSON, try standard parsing (will raise appropriate error)
        if not all_args:
            all_args = [json.loads(args_str)]
        
        # Execute the tool for each set of arguments and combine results
        results = []
        for args in all_args:
            result = str(self.execute_tool(tool_name=tool_call["name"], args=args))
            results.append(result)
        
        # Combine all results
        combined_result = "\n\n---\n\n".join(results) if len(results) > 1 else results[0]

        tool_call_output = self.create_function_call_output_item(tool_call["call_id"], combined_result)
        messages.append(tool_call_output)
        return ResponsesAgentStreamEvent(type="response.output_item.done", item=tool_call_output)

    def call_and_run_tools(
        self,
        messages: list[dict[str, Any]],
        max_iter: int = 20,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        for _ in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages)
            else:
                yield from self.output_to_responses_items_stream(
                    chunks=self.call_llm(messages), aggregator=messages
                )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item("Max iterations reached. The agent called and searched the codebase and documentation multiple times without finding the answer. Please try reformulating the answer.", str(uuid4())),
        )

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            i.model_dump() for i in request.input
        ]
        yield from self.call_and_run_tools(messages=messages)


# Create agent instance (tracing already enabled above)
AGENT = ToolCallingAgent(llm_endpoint=LLM_ENDPOINT_NAME, tools=TOOL_INFOS)
mlflow.models.set_model(AGENT)

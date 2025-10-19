import json
import warnings
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
# Define your system prompt
############################################

LLM_ENDPOINT_NAME = "databricks-claude-sonnet-4"

SYSTEM_PROMPT = """
You are a UCX (Databricks Unity Catalog Migration Assistant) expert assistant with access to the UCX codebase and documentation. UCX is a framework that automates migration processes including assessment, group migration, table migration, and code migration steps.

RESPONSE GUIDELINES:
- Be concise and direct unless the user requests details or clarification is essential. Do not overexplain or make assumptions. Aim for at maximum 200 words (unless absolutely necessary)
- Verify all functionality and commands exist in the codebase/documentation before confirming them
- If information is unavailable or uncertain, clearly state that you don't have enough information to answer this.

REASONING PROCESS:
- Before calling any tool, explain what information you're looking for and why
- After receiving tool results, analyze what you learned and determine if you need more information
- If you need to call multiple tools, explain your strategy first
- Synthesize information from multiple sources before providing your final answer

CRITICAL CONSIDERATIONS:
- Cloud platform differences: Azure and AWS have fuller support; GCP functionality is significantly more limited
- Managed vs. External: Be careful between these types of tables. Also be careful with table formats. For example: External Delta table might not have the same migration pattern as an external Parquet table.
- Do not get confused between different ACL types: Databricks Workspace ACLs, Unity Catalog ACLs, and cloud provider ACLs
- Out-of-the-box usage: UCX is designed for use without code modifications. Users will call the UCX CLI or trigger Databricks Workflows. They are not supposed to interact with specific python functions that are inside the library.
- If a feature doesn't exist but could be easily implemented, suggest the user request it from the UCX development team rather than implementing it themselves

VALIDATION RULES:
- Never say a feature exists based solely on user questions. Validate with the codebase and documentation
- Never say a command exists without verification. Validate with the codebase and documentation
- Only say something is possible after validating with the codebase and documentation
"""

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

VECTOR_SEARCH_TOOLS.append(
  VectorSearchRetrieverTool(
    index_name="btafur_catalog.default.ucx_documentation_vector",
    tool_name="docs_retriever",
    doc_uri="file_url",
    tool_description="Retrieves UCX documentation including user guides, CLI commands, workflow descriptions, and feature explanations. Use this for understanding user-facing functionality and usage patterns. But always confirm with the codebase",
    num_results=10
    
  )
)
VECTOR_SEARCH_TOOLS.append(
  VectorSearchRetrieverTool(
    index_name="btafur_catalog.default.ucx_codebase_vector",
    tool_name="codebase_retriever",
    doc_uri="file_url",
    tool_description="Retrieves UCX source code including Python/SQL function definitions, classes, and implementation details. Use this to verify implementation details, validate that features exist, or understand technical internals. Always cross-reference with documentation to confirm user-facing availability.",
    num_results=8
  )
)

for vs_tool in VECTOR_SEARCH_TOOLS:
    TOOL_INFOS.append(create_tool_info(vs_tool.tool, vs_tool.execute))


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
                temperature=0.01,
            ):
                yield chunk.to_dict()

    def handle_tool_call(
        self, tool_call: dict[str, Any], messages: list[dict[str, Any]]
    ) -> ResponsesAgentStreamEvent:
        """
        Execute tool calls, add them to the running message history, and return a ResponsesStreamEvent w/ tool output
        """
        args = json.loads(tool_call["arguments"])
        result = str(self.execute_tool(tool_name=tool_call["name"], args=args))

        tool_call_output = self.create_function_call_output_item(tool_call["call_id"], result)
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


mlflow.openai.autolog()
AGENT = ToolCallingAgent(llm_endpoint=LLM_ENDPOINT_NAME, tools=TOOL_INFOS)
mlflow.models.set_model(AGENT)

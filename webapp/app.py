
import logging
import os
import time
import uuid
import streamlit as st
from model_serving_utils import (
    query_endpoint, 
    query_endpoint_stream, 
    _get_endpoint_task_type,
)
from ucx_utils import UCXTroubleshooter
from audit_utils import get_auditor, PrivacyManager
from simple_audit_utils import get_simple_auditor
from collections import OrderedDict
from messages import UserMessage, AssistantResponse, render_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _extract_doc_sources_from_tool_messages(thinking_messages):
    """Extract unique doc_uri values from tool messages."""
    import json
    import ast
    
    logger.info(f"🔍 _extract_doc_sources_from_tool_messages called with {len(thinking_messages)} messages")
    
    doc_sources = set()
    
    for idx, msg in enumerate(thinking_messages):
        logger.info(f"  Message {idx}: role={msg.get('role')}")
        
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            logger.info(f"  📦 Tool message {idx}, content length: {len(content)}")
            logger.info(f"  📦 First 500 chars: {content[:500]}")
            
            try:
                # Try JSON first
                try:
                    data = json.loads(content)
                    logger.info(f"  ✅ Parsed as JSON")
                except json.JSONDecodeError:
                    # Fall back to Python literal eval
                    logger.info(f"  ⚠️ Not JSON, trying ast.literal_eval...")
                    data = ast.literal_eval(content)
                    logger.info(f"  ✅ Parsed as Python literal")
                
                logger.info(f"  ✅ Data type: {type(data)}")
                
                if isinstance(data, list):
                    logger.info(f"  📋 List with {len(data)} items")
                    
                    for item_idx, item in enumerate(data):
                        if isinstance(item, dict):
                            if 'metadata' in item:
                                metadata = item['metadata']
                                
                                if isinstance(metadata, dict):
                                    doc_uri = metadata.get('doc_uri')
                                    
                                    if doc_uri:
                                        doc_sources.add(doc_uri)
                                        logger.info(f"    ✅ Added source: {doc_uri}")
                                    else:
                                        # Log what keys ARE available
                                        if item_idx < 3:  # Only log first 3
                                            logger.warning(f"    ⚠️ Item {item_idx} metadata keys: {list(metadata.keys())}")
                else:
                    logger.warning(f"  ⚠️ Data is not a list, it's: {type(data)}")
                    
            except Exception as e:
                logger.error(f"  ❌ Error parsing content: {e}", exc_info=True)
    
    logger.info(f"🎯 Total sources found: {len(doc_sources)}")
    if doc_sources:
        logger.info(f"📚 Sources: {list(doc_sources)}")
    else:
        logger.warning("⚠️ No sources found!")
    
    return doc_sources

SERVING_ENDPOINT = os.getenv('SERVING_ENDPOINT')
assert SERVING_ENDPOINT, \
    ("Unable to determine serving endpoint to use for chatbot app. If developing locally, "
     "set the SERVING_ENDPOINT environment variable to the name of your serving endpoint. If "
     "deploying to a Databricks app, include a serving endpoint resource named "
     "'serving_endpoint' with CAN_QUERY permissions, as described in "
     "https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app#deploy-the-databricks-app")

def get_user_info():
    headers = st.context.headers
    return dict(
        user_name=headers.get("X-Forwarded-Preferred-Username"),
        user_email=headers.get("X-Forwarded-Email"),
        user_id=headers.get("X-Forwarded-User"),
    )

user_info = get_user_info()

# Initialize audit logging with true Delta Lake via SQL
logger.info("🚀 Starting audit system initialization...")
try:
    from sql_audit_utils import get_sql_auditor
    logger.info("📊 Attempting SQL-based Delta Lake auditor...")
    auditor = get_sql_auditor()
    
    # Check if it's really working or fell back to JSON
    if hasattr(auditor, '_use_fallback') and auditor._use_fallback:
        logger.warning("⚠️ SQL auditor fell back to JSON mode")
        audit_mode = "fallback"
    else:
        audit_mode = "sql_warehouse"
        logger.info("✅ SQL-based Delta Lake auditor initialized successfully!")
        
except Exception as e:
    import traceback
    logger.error(f"❌ SQL Delta auditor initialization failed: {e}")
    logger.error(f"Full traceback: {traceback.format_exc()}")
    logger.warning("⚠️ Falling back to simulation mode...")
    try:
        from simple_audit_utils import get_simple_auditor
        auditor = get_simple_auditor()
        audit_mode = "delta_simulation"
        logger.info("✅ Using Delta simulation as fallback")
    except Exception as e2:
        logger.error(f"❌ All Delta auditors failed: {e2}")
        logger.warning("⚠️ Using JSON fallback mode")
        auditor = get_auditor()
        audit_mode = "fallback"

logger.info(f"🎯 Final audit mode: {audit_mode}")
logger.info(f"🔧 Auditor type: {type(auditor).__name__}")

# Generate session ID for audit tracking
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Display audit configuration in debug mode (optional)
if os.getenv('AUDIT_DEBUG', 'false').lower() == 'true':
    audit_config = {
        'table': os.getenv('AUDIT_TABLE', 'chat_interactions')
    }
    logger.info(f"Audit configuration: {audit_config}")

# Streamlit app
if "visibility" not in st.session_state:
    st.session_state.visibility = "visible"
    st.session_state.disabled = False

st.title("🔧 UCX Troubleshooting Assistant")

# Check for admin dashboard access via URL parameters
admin_access = False
diagnostics_access = False

# Check session state for manual triggers
if "test_admin" in st.session_state and st.session_state.test_admin:
    admin_access = True
if "test_debug" in st.session_state and st.session_state.test_debug:
    diagnostics_access = True

# Check for admin access via URL parameters  
try:
    # Check for admin parameter
    admin_param = st.query_params.get('admin', '')
    debug_param = st.query_params.get('debug', '')
    
    if admin_param == 'dashboard':
        st.session_state.test_admin = True
        st.session_state.test_debug = False
        admin_access = True
    elif debug_param == 'spark':
        st.session_state.test_debug = True
        st.session_state.test_admin = False  
        diagnostics_access = True
    # If no URL params, preserve existing session state
    elif "test_admin" in st.session_state and st.session_state.test_admin:
        admin_access = True
    elif "test_debug" in st.session_state and st.session_state.test_debug:
        diagnostics_access = True
        
except Exception as e:
    # Fallback to session state
    if "test_admin" in st.session_state and st.session_state.test_admin:
        admin_access = True
    elif "test_debug" in st.session_state and st.session_state.test_debug:
        diagnostics_access = True

# Show audit dashboard if accessed with special URL parameter
if admin_access:
    st.info("🔒 **Admin Access Detected** - Showing Audit Dashboard")
    
    # Pass the same auditor instance to the dashboard
    from audit_dashboard import AuditDashboard
    dashboard = AuditDashboard()
    dashboard.auditor = auditor  # Use the same auditor as main app
    dashboard.audit_mode = audit_mode
    dashboard.render()

    # Log admin access
    auditor.log_interaction(
        session_id=st.session_state.session_id,
        user_info=user_info,
        user_question="Admin Dashboard Access",
        assistant_response="Accessed audit dashboard via admin URL",
        response_time_ms=0,
        endpoint_used="N/A",
        interaction_type="admin_access",
        ucx_context_used=False
    )

    # Stop here - don't show the normal app interface
    st.stop()

# Show Spark diagnostics if accessed with special URL parameter
if diagnostics_access:
    st.info("🔍 **Debug Mode** - SQL Warehouse & Environment Diagnostics")
    
    # Check current auditor mode
    st.subheader("📊 Current Audit Mode")
    if audit_mode == "sql_warehouse":
        st.success("✅ Using SQL Warehouse Delta Lake mode")
        st.info("🏛️ Real Delta tables with full ACID capabilities!")
        st.code(f"Active auditor: {type(auditor).__name__}")
        st.code(f"Table: {auditor.full_table_name}")
        st.code(f"Warehouse: {auditor.warehouse.id if hasattr(auditor, 'warehouse') else 'Not set'}")
    elif audit_mode == "delta_simulation":
        st.success("✅ Using Delta Table simulation mode")
        st.info("🎯 JSON backend with Delta Table presentation - best UX!")
        st.code(f"Active auditor: {type(auditor).__name__}")
        
        # Show connection status
        if hasattr(auditor, 'databricks_connected') and auditor.databricks_connected:
            st.success("✅ Connected to Databricks workspace")
        else:
            st.warning("⚠️ Not connected to workspace (expected in local testing)")
    else:
        st.warning("⚠️ Using JSON fallback audit mode") 
        st.code(f"Active auditor: {type(auditor).__name__}")
    
    st.stop()

# Add UCX-specific sidebar
with st.sidebar:
    st.header("🛠️ UCX Tools")
    
    if st.button("📋 Installation Checklist"):
        troubleshooter = UCXTroubleshooter()
        checklist = troubleshooter.get_installation_checklist()
        st.write("### Installation Checklist")
        for item in checklist:
            st.write(item)
        
        # Log checklist interaction
        auditor.log_interaction(
            session_id=st.session_state.session_id,
            user_info=user_info,
            user_question="Requested Installation Checklist",
            assistant_response=f"Provided {len(checklist)} installation checklist items",
            response_time_ms=0,
            endpoint_used="N/A",
            interaction_type="checklist",
            ucx_context_used=False
        )
    
    if st.button("🔍 Assessment Checklist"):
        troubleshooter = UCXTroubleshooter()
        checklist = troubleshooter.get_assessment_checklist()
        st.write("### Assessment Checklist")
        for item in checklist:
            st.write(item)
        
        # Log checklist interaction
        auditor.log_interaction(
            session_id=st.session_state.session_id,
            user_info=user_info,
            user_question="Requested Assessment Checklist",
            assistant_response=f"Provided {len(checklist)} assessment checklist items",
            response_time_ms=0,
            endpoint_used="N/A",
            interaction_type="checklist",
            ucx_context_used=False
        )
    
    if st.button("📚 Common Errors"):
        troubleshooter = UCXTroubleshooter()
        errors = troubleshooter.get_common_errors()
        st.write("### Common UCX Errors")
        for error_key, error_info in errors.items():
            with st.expander(f"🚨 {error_info['error']}"):
                st.write(f"**Solution:** {error_info['solution']}")
                st.write(f"**Details:** {error_info['details']}")
        
        # Log common errors interaction
        auditor.log_interaction(
            session_id=st.session_state.session_id,
            user_info=user_info,
            user_question="Requested Common Errors Guide",
            assistant_response=f"Provided {len(errors)} common error solutions",
            response_time_ms=0,
            endpoint_used="N/A",
            interaction_type="common_errors",
            ucx_context_used=False
        )

st.markdown(
    "💡 **UCX Troubleshooting Assistant** - Get help with Unity Catalog Migration issues, "
    "installation problems, and assessment errors. Describe your issue and I'll provide specific guidance!"
)

# Initialize chat history
if "history" not in st.session_state:
    st.session_state.history = []


def reduce_chat_agent_chunks(chunks):
    """
    Reduce a list of ChatAgentChunk objects corresponding to a particular
    message into a single ChatAgentMessage
    """
    deltas = [chunk.delta for chunk in chunks]
    first_delta = deltas[0]
    result_msg = first_delta
    msg_contents = []
    
    # Accumulate tool calls properly
    tool_call_map = {}  # Map call_id to tool call for accumulation
    
    for delta in deltas:
        # Handle content
        if delta.content:
            msg_contents.append(delta.content)
            
        # Handle tool calls
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            for tool_call in delta.tool_calls:
                call_id = getattr(tool_call, 'id', None)
                tool_type = getattr(tool_call, 'type', "function")
                function_info = getattr(tool_call, 'function', None)
                if function_info:
                    func_name = getattr(function_info, 'name', "")
                    func_args = getattr(function_info, 'arguments', "")
                else:
                    func_name = ""
                    func_args = ""
                
                if call_id:
                    if call_id not in tool_call_map:
                        # New tool call
                        tool_call_map[call_id] = {
                            "id": call_id,
                            "type": tool_type,
                            "function": {
                                "name": func_name,
                                "arguments": func_args
                            }
                        }
                    else:
                        # Accumulate arguments for existing tool call
                        existing_args = tool_call_map[call_id]["function"]["arguments"]
                        tool_call_map[call_id]["function"]["arguments"] = existing_args + func_args

                        # Update function name if provided
                        if func_name:
                            tool_call_map[call_id]["function"]["name"] = func_name

        # Handle tool call IDs (for tool response messages)
        if hasattr(delta, 'tool_call_id') and delta.tool_call_id:
            result_msg = result_msg.model_copy(update={"tool_call_id": delta.tool_call_id})
    
    # Convert tool call map back to list
    if tool_call_map:
        accumulated_tool_calls = list(tool_call_map.values())
        result_msg = result_msg.model_copy(update={"tool_calls": accumulated_tool_calls})
    
    result_msg = result_msg.model_copy(update={"content": "".join(msg_contents)})
    return result_msg


def query_endpoint_and_render(task_type, input_messages):
    """Handle streaming response based on task type."""
    if task_type == "agent/v1/responses":
        return query_responses_endpoint_and_render(input_messages)
    elif task_type == "agent/v2/chat":
        return query_chat_agent_endpoint_and_render(input_messages)
    else:  # chat/completions
        return query_chat_completions_endpoint_and_render(input_messages)


def query_chat_completions_endpoint_and_render(input_messages):
    """Handle ChatCompletions streaming format."""
    with st.chat_message("assistant"):
        response_area = st.empty()
        response_area.markdown("_Thinking..._")
        
        accumulated_content = ""
        request_id = None
        
        try:
            for chunk in query_endpoint_stream(
                endpoint_name=SERVING_ENDPOINT,
                messages=input_messages,
                return_traces=True
            ):
                if "choices" in chunk and chunk["choices"]:
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        accumulated_content += content
                        response_area.markdown(accumulated_content)
                
                if "databricks_output" in chunk:
                    req_id = chunk["databricks_output"].get("databricks_request_id")
                    if req_id:
                        request_id = req_id
            
            return AssistantResponse(
                messages=[{"role": "assistant", "content": accumulated_content}],
                request_id=request_id
            )
        except Exception:
            response_area.markdown("_Ran into an error. Retrying without streaming..._")
            messages, request_id = query_endpoint(
                endpoint_name=SERVING_ENDPOINT,
                messages=input_messages,
                return_traces=True
            )
            response_area.empty()
            with response_area.container():
                for message in messages:
                    render_message(message)
            return AssistantResponse(messages=messages, request_id=request_id)


def query_chat_agent_endpoint_and_render(input_messages):
    """Handle ChatAgent streaming format."""
    from mlflow.types.agent import ChatAgentChunk
    
    with st.chat_message("assistant"):
        response_area = st.empty()
        response_area.markdown("_Thinking..._")
        
        message_buffers = OrderedDict()
        request_id = None
        
        try:
            for raw_chunk in query_endpoint_stream(
                endpoint_name=SERVING_ENDPOINT,
                messages=input_messages,
                return_traces=True
            ):
                response_area.empty()
                chunk = ChatAgentChunk.model_validate(raw_chunk)
                delta = chunk.delta
                message_id = delta.id

                req_id = raw_chunk.get("databricks_output", {}).get("databricks_request_id")
                if req_id:
                    request_id = req_id
                if message_id not in message_buffers:
                    message_buffers[message_id] = {
                        "chunks": [],
                        "render_area": st.empty(),
                    }
                message_buffers[message_id]["chunks"].append(chunk)
                
                partial_message = reduce_chat_agent_chunks(message_buffers[message_id]["chunks"])
                render_area = message_buffers[message_id]["render_area"]
                message_content = partial_message.model_dump_compat(exclude_none=True)
                with render_area.container():
                    render_message(message_content)
            
            messages = []
            for msg_id, msg_info in message_buffers.items():
                messages.append(reduce_chat_agent_chunks(msg_info["chunks"]))
            
            return AssistantResponse(
                messages=[message.model_dump_compat(exclude_none=True) for message in messages],
                request_id=request_id
            )
        except Exception:
            response_area.markdown("_Ran into an error. Retrying without streaming..._")
            messages, request_id = query_endpoint(
                endpoint_name=SERVING_ENDPOINT,
                messages=input_messages,
                return_traces=True
            )
            response_area.empty()
            with response_area.container():
                for message in messages:
                    render_message(message)
            return AssistantResponse(messages=messages, request_id=request_id)


# In app.py, update the query_responses_endpoint_and_render function:
def query_responses_endpoint_and_render(input_messages):
    """Handle ResponsesAgent streaming format using MLflow types with collapsed thinking."""
    from mlflow.types.responses import ResponsesAgentStreamEvent
    
    with st.chat_message("assistant"):
        # Create containers for thinking and final response
        thinking_container_placeholder = st.empty()
        response_area = st.empty()
        
        # Track all events in order
        all_events = []
        all_messages = []
        thinking_messages = []
        final_message_content = ""
        request_id = None
        current_step = "🤔 Thinking process..."

        try:
            for raw_event in query_endpoint_stream(
                endpoint_name=SERVING_ENDPOINT,
                messages=input_messages,
                return_traces=True
            ):
                if "databricks_output" in raw_event:
                    req_id = raw_event["databricks_output"].get("databricks_request_id")
                    if req_id:
                        request_id = req_id
                
                if "type" not in raw_event:
                    continue
                
                if raw_event.get("type") != "response.output_item.done":
                    continue
                    
                try:
                    event = ResponsesAgentStreamEvent.model_validate(raw_event)
                    
                    if not hasattr(event, 'item') or not event.item:
                        continue
                    
                    all_events.append(event.item)
                    item = event.item
                    item_type = item.get("type")
                    
                    if item_type == "function_call":
                        call_id = item.get("call_id")
                        function_name = item.get("name")
                        arguments = item.get("arguments", "")
                        
                        # Update current step
                        current_step = f"🛠️ Calling {function_name}..."
                        
                        tool_msg = {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": arguments
                                }
                            }]
                        }
                        
                        all_messages.append(tool_msg)
                        thinking_messages.append(tool_msg)
                        
                        # Re-render the expander with updated label
                        with thinking_container_placeholder.container():
                            with st.expander(current_step, expanded=False):
                                for msg in thinking_messages:
                                    render_message(msg)
                        
                    elif item_type == "function_call_output":
                        call_id = item.get("call_id")
                        output = item.get("output", "")
                        
                        # Update current step
                        current_step = "🧰 Processing tool response..."
                        
                        tool_output_msg = {
                            "role": "tool",
                            "content": output,
                            "tool_call_id": call_id
                        }
                        
                        all_messages.append(tool_output_msg)
                        thinking_messages.append(tool_output_msg)
                        
                        # Re-render the expander with updated label
                        with thinking_container_placeholder.container():
                            with st.expander(current_step, expanded=False):
                                for msg in thinking_messages:
                                    render_message(msg)
                        
                    elif item_type == "message":
                        # Update current step
                        current_step = "💭 Formulating answer..."
                        
                        # Re-render the expander with updated label
                        with thinking_container_placeholder.container():
                            with st.expander(current_step, expanded=False):
                                for msg in thinking_messages:
                                    render_message(msg)
                        
                        content_parts = item.get("content", [])
                        message_text = ""
                        
                        for content_part in content_parts:
                            if content_part.get("type") == "output_text":
                                text = content_part.get("text", "")
                                message_text += text
                        
                        if message_text:
                            all_messages.append({
                                "role": "assistant",
                                "content": message_text
                            })
                
                except Exception as e:
                    logger.debug(f"Error processing event: {e}")
                    continue
            
            # Final render with "Done" label
            with thinking_container_placeholder.container():
                with st.expander("✅ Done", expanded=False):
                    for msg in thinking_messages:
                        render_message(msg)
            
            # Extract the final answer
            message_items = [e for e in all_events if e.get("type") == "message"]
            
            if message_items:
                final_message = message_items[-1]
                for content_part in final_message.get("content", []):
                    if content_part.get("type") == "output_text":
                        final_message_content += content_part.get("text", "")
            
            # Display final answer
            if final_message_content:
                response_area.markdown(final_message_content)
            else:
                response_area.markdown("_Response completed. See thinking process above._")
            
            # Extract and display sources
            logger.info("🚀 About to extract doc sources...")
            doc_sources = _extract_doc_sources_from_tool_messages(thinking_messages)
            logger.info(f"🚀 Extraction complete, found {len(doc_sources)} sources")
            
            if doc_sources:
                logger.info("✅ Rendering sources section...")
                st.markdown("---")
                st.markdown("📚 **Sources read by assistant:**")
                
                if len(doc_sources) == 1:
                    source = list(doc_sources)[0]
                    logger.info(f"Rendering single source: {source}")
                    st.markdown(f"[{source}]({source})")
                else:
                    logger.info(f"Rendering {len(doc_sources)} sources in columns...")
                    cols = st.columns(min(len(doc_sources), 3))
                    for idx, source in enumerate(sorted(doc_sources)):
                        col_idx = idx % len(cols)
                        with cols[col_idx]:
                            filename = source.split('/')[-1] if '/' in source else source
                            st.markdown(f"[{filename}]({source})")
                logger.info("✅ Sources section rendered")
            else:
                logger.warning("⚠️ No sources to render")
            
            logger.info(f"Creating AssistantResponse with {len(thinking_messages)} thinking messages")
            for msg in thinking_messages:
                if msg.get("role") == "tool":
                    logger.info(f"Tool message content length: {len(msg.get('content', ''))}")
            
            return AssistantResponse(
                messages=all_messages,
                request_id=request_id,
                thinking_messages=thinking_messages,
                final_content=final_message_content
            )
            
        except Exception as e:
            logger.warning(f"Streaming failed: {e}", exc_info=True)
            response_area.markdown("_Ran into an error. Retrying without streaming..._")
            messages, request_id = query_endpoint(
                endpoint_name=SERVING_ENDPOINT,
                messages=input_messages,
                return_traces=True
            )
            response_area.empty()
            
            # Separate by message structure
            tool_msgs = []
            final_msgs = []
            
            for message in messages:
                if isinstance(message, dict):
                    if message.get("tool_calls") or message.get("role") == "tool":
                        tool_msgs.append(message)
                    elif message.get("role") == "assistant":
                        final_msgs.append(message)
            
            # Take only the last assistant message as final answer
            final_content = ""
            if final_msgs:
                final_content = final_msgs[-1].get("content", "")
                final_msgs = [final_msgs[-1]]
            
            # Render thinking in expander with "Done" label
            if tool_msgs:
                with thinking_container_placeholder.container():
                    with st.expander("✅ Done", expanded=False):
                        for msg in tool_msgs:
                            render_message(msg)
            
            # Render final answer
            if final_msgs:
                with response_area.container():
                    for message in final_msgs:
                        render_message(message)
            else:
                with response_area.container():
                    for message in messages:
                        render_message(message)
            
            logger.info(f"Fallback: Creating AssistantResponse with {len(tool_msgs)} thinking messages")
                    
            return AssistantResponse(
                messages=messages,
                request_id=request_id,
                thinking_messages=tool_msgs,
                final_content=final_content
            )

# --- Render chat history ---
for i, element in enumerate(st.session_state.history):
    element.render(i)


# --- Chat input (must run BEFORE rendering messages) ---
prompt = st.chat_input("Describe your UCX issue or ask any Unity Catalog migration question...")
if prompt:
    # Start timing for audit logging
    start_time = time.time()
    
    # Detect error type from user prompt
    error_type_detected = None
    if any(keyword in prompt.lower() for keyword in ['error', 'fail', 'issue', 'problem', 'trouble']):
        # Try to classify the error type
        troubleshooter = UCXTroubleshooter()
        error_analysis = troubleshooter.analyze_error_message(prompt)
        error_type_detected = error_analysis.get('error', 'Unknown error')
    
    # Get the task type for this endpoint
    task_type = _get_endpoint_task_type(SERVING_ENDPOINT)
    
    # Add user message to chat history
    user_msg = UserMessage(content=prompt)
    st.session_state.history.append(user_msg)
    user_msg.render(len(st.session_state.history) - 1)
    
    # Convert history to standard chat message format for the query methods
    input_messages = [msg for elem in st.session_state.history for msg in elem.to_input_messages()]
    
    # Handle the response using the appropriate handler
    assistant_response = query_endpoint_and_render(task_type, input_messages)
    
    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Extract text content from assistant response for audit logging
    response_text = ""
    for msg in assistant_response.messages:
        if isinstance(msg, dict) and msg.get("content"):
            response_text += msg.get("content", "")
    
    # Apply privacy redaction to sensitive content
    safe_prompt = PrivacyManager.redact_sensitive_content(prompt)
    safe_response = PrivacyManager.redact_sensitive_content(response_text)
    
    # Log the interaction
    auditor.log_interaction(
        session_id=st.session_state.session_id,
        user_info=user_info,
        user_question=safe_prompt,
        assistant_response=safe_response,
        response_time_ms=response_time_ms,
        endpoint_used=SERVING_ENDPOINT,
        interaction_type="chat",
        ucx_context_used=False,
        error_type_detected=error_type_detected
    )
    
    # Add assistant response to history
    st.session_state.history.append(assistant_response)
    # Generate PDF content once and store in session state to prevent button disappearing
    pdf_session_key = f"pdf_data_{hash(response_text)}"
    
    if pdf_session_key not in st.session_state:
        try:
            import io
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            
            # Generate PDF content
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add content
            story.append(Paragraph("UCX Troubleshooting Assistant Response", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph(f"Question: {prompt}", styles['Normal']))
            story.append(Spacer(1, 12))
            
            story.append(Paragraph("Response", styles['Heading2']))
            
            # Clean response for PDF
            clean_response = response_text.replace('**', '').replace('#', '').replace('*', '')
            paragraphs = clean_response.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), styles['Normal']))
            
            doc.build(story)
            st.session_state[pdf_session_key] = pdf_buffer.getvalue()
            pdf_buffer.close()
            
        except Exception as e:
            st.session_state[pdf_session_key] = None
            logger.error(f"PDF generation failed: {e}")
    
    # Compact download section with persistent button
    if st.session_state.get(pdf_session_key):
        # Create a unique persistent key that won't change on rerun
        persistent_key = f"pdf_download_{abs(hash(response_text))}"
        
        # Mark this response as having a download available
        if f"has_download_{persistent_key}" not in st.session_state:
            st.session_state[f"has_download_{persistent_key}"] = True
        
        st.markdown("---")
        
        # Compact download area
        col1, col2 = st.columns([4, 1])
        
        with col1:
            word_count = len(response_text.split())
            st.markdown(f"**💾 Download available** • {word_count} words • Ready for customer documentation")
        
        with col2:
            # Small icon-sized download button that persists
            st.download_button(
                label="📄",
                data=st.session_state[pdf_session_key],
                file_name=f"UCX_Response_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                help="Download PDF report",
                key=persistent_key,
                type="secondary"
            )
    
    # Add assistant response to chat history
    st.session_state.history.append(assistant_response)